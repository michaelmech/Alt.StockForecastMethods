# -*- coding: utf-8 -*-
"""Delphi_Nowcaster

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JGg2iPqO6t2WlzWIORrE5oIdam2V8fR0
"""

!pip install tweepy
!pip install PyPortfolioOpt
!pip install -U yfinance
!pip install td-ameritrade-python-api==0.3.5

!pip install --upgrade ta
!pip install -U git+https://github.com/twopirllc/pandas-ta

import numpy as np
import pandas as pd
import sklearn
import datetime
import matplotlib.pyplot as plt

from tweepy import OAuthHandler
from tweepy import API
from tweepy import Cursor
import tweepy

import pandas_ta
import pandas_datareader.data as pdr
import ta

import yfinance as yf
yf.pdr_override()

import td
from td.client import TDClient

import pypfopt

from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
import nltk
import time

import warnings
warnings.simplefilter("ignore")

nltk.download('vader_lexicon')
nltk.download('stopwords')

def yf_fetch(ticker_list):
 
  returns_df=pd.DataFrame()
  prices_df=pd.DataFrame()
 
  for ticker in ticker_list:
    data=yf.Ticker(ticker).history(period='max')
   
    data['returns']=data.Close.pct_change()
 
    returns_df[str(ticker)]=data['returns']
    prices_df[str(ticker)]=data['Close']
  
  return returns_df,prices_df

def Blacklitter(prices_df,view_dict):
  risk_model=pypfopt.risk_models.CovarianceShrinkage(prices_df)
  cov_matrix=risk_model.oracle_approximating()
 
  view_series=pd.Series(view_dict)
 
  #cov_matrix=pypfopt.risk_models.fix_nonpositive_semidefinite(cov_matrix,fix_method='spectral')
 
  #if np.linalg.det(cov_matrix)==0:
    #cov_matrix=cov_matrix+0.0000001
  
  bl=pypfopt.black_litterman.BlackLittermanModel(cov_matrix=cov_matrix,absolute_views=view_series)
 
  weights=bl.bl_weights()
  weights=bl.clean_weights(cutoff=0.000001,rounding=8)
 
  return dict(weights)

def Blacklitter2(prices_df,views_dict,method):
  view_series=pd.Series(views_dict)
  view_series=view_series[view_series!=0]
  hrp_weights=HR_Paritize(prices_df,views_dict,method)
  hrp_series=pd.Series(hrp_weights) 
 
  risk_model=pypfopt.risk_models.CovarianceShrinkage(prices_df)
  cov_matrix=risk_model.oracle_approximating()
 
  repeat=np.array(hrp_series-1/len(hrp_series))
  P=np.vstack([repeat]*len(view_series))
  Q=np.array(view_series).reshape(-1,1)
 
  bl=pypfopt.black_litterman.BlackLittermanModel(cov_matrix=cov_matrix,Q=Q,P=P)
  weights=bl.bl_weights()
  weights=bl.clean_weights(cutoff=0.000001,rounding=8)
 
  if np.isinf(pd.Series(weights)).sum()==len(weights):
    one_df=pd.Series([1 if x>0 else -1 for x in pd.Series(weights)],index=weights.keys())
    
    one_df=one_df/(abs(one_df)).sum()
    weights=dict(one_df)
 
  return dict(weights)

def HR_Paritize(prices_df,views_dict,method='median'):
 
  if len(views_dict)==1:
    return {x:1 for x in views_dict}
  
  elif len(views_dict)==0:
    return {}
  
  else:
    
    views_df=pd.Series(views_dict)
 
    prices_df=prices_df[views_df.index]
 
    risk_model=pypfopt.risk_models.CovarianceShrinkage(prices_df)
    cov_matrix=risk_model.oracle_approximating()
 
    hrp=pypfopt.hierarchical_portfolio.HRPOpt(cov_matrix=cov_matrix)
 
    abs_weights=dict(hrp.optimize(method))
    
    return abs_weights

def get_shares(tweets_df,capital,bl1=False,long_only=False):
  recent_df=tweets_df.copy()
  mean_df=recent_df.groupby('tickers').mean()
  mean_df=mean_df[abs(mean_df)>0.25].dropna()
  
  views_dict={x:y for x,y in zip(mean_df.index,mean_df['sent_scores'])}

  ticker_list=recent_df['tickers']
  _,prime_prices_df=yf_fetch(ticker_list)
  last_prices=prime_prices_df.iloc[-1] 

  if long_only:
    views_dict={x:y for x,y in views_dict.items() if y>0}

  if bl1:
    bl_weights=Blacklitter(prime_prices_df[views_dict.keys()],views_dict) 

  else:
    bl_weights=Blacklitter2(prime_prices_df[views_dict.keys()],views_dict,'median')

  weights_df=pd.Series(bl_weights)

  if long_only:
    if len(weights_df[weights_df>0])>0:
      weights_df=weights_df[weights_df>0]

  if abs(weights_df).sum()!=1:
    weights_df=weights_df/abs(weights_df).sum() 

  sign_df=weights_df/abs(weights_df)

  abs_weights=dict(abs(weights_df))

  sharer=pypfopt.discrete_allocation.DiscreteAllocation(abs_weights,last_prices,capital,0.000001) #0.000001
  
  shares_dict=sharer.greedy_portfolio()[0]

  #shares_dict={key:abs_weights[key]*capital for key in abs_weights}

  shares_dict={key:shares_dict[key]*sign_df[key] for key in shares_dict}

  return shares_dict

def Crypto_Fix(tweet_df):

  crypto_list=['etc','btc','doge','ada','eth','shib']

  for i in tweet_df['tickers']:
    if i.lower() in crypto_list:
      tweet_df['tickers'][tweet_df['tickers']==i]=i.lower()+'-usd'
  
  return tweet_df

key= '********************'

secret= '********************************'

auth = tweepy.AppAuthHandler(key, secret)

api = tweepy.API(auth)

accounts_list=['1charts6','markminervini','saxena_puru','Trendspider_J','TraderLion_','RayTL_','801010athlete','RichardMoglen','LeifSoreide','LuoshengPeng','GregDuncan_','Trader_mcaruso','SSalim0002',
               'alphatrends','cperruna','PatternProfits','ThetaWarrior','TrendSpider','ChartingOptions','alphacharts365','TradeSniperSara','ACInvestorBlog','DanZanger','traderstewie','commander10','SmartContracter','TraderSimon',
               'Fibonacciqueen','MysteryTrader99']

def yahooTA(ticker,freq):
  
  sixty=['1m','2m','5m','15m','30m','15m']
 
  if freq in sixty:
    data=pdr.get_data_yahoo(ticker,interval=freq,period='60d')
    data.index=data.index.tz_convert('US/Pacific')
  
  elif freq=='1h':
    data=pdr.get_data_yahoo(ticker,interval=freq,period='710d')
    data.index=data.index.tz_convert('US/Pacific')
  
  elif freq=='1d' or freq=='1wk':
    #data=pdr.get_data_yahoo(ticker,interval=freq)
    data=pdr.get_data_yahoo(ticker,interval=freq,period='360d')
  
  elif freq=='1mo':
    data=pdr.get_data_yahoo(ticker,interval=freq,period='1200d')
   
  data=data.drop('Adj Close',axis=1)
  #data=data.reset_index()
  
  data['mfi2']=ta.volume.money_flow_index(high=data['High'],low=data['Low'],close=data['Close'],volume=data['Volume'],window=2)
  data['mfi10']=ta.volume.money_flow_index(high=data['High'],low=data['Low'],close=data['Close'],volume=data['Volume'],window=10)
  
  data['rsi10']=ta.momentum.rsi(close=data['Close'],window=10)
  data['rsi2']=ta.momentum.rsi(close=data['Close'],window=2)            
 
  data['hma10']=pandas_ta.hma(data['Close'],length=10)
  data['hma20']=pandas_ta.hma(data['Close'],length=20)
  data['hma50']=pandas_ta.hma(data['Close'],length=50)
  #data['hma150']=pandas_ta.hma(data['Close'],length=150)
  #data['ema200']=ta.trend.ema_indicator(data['Close'],window=200)
  data['ema10']=pandas_ta.ema(data['Close'],length=10)
  data['ema20']=pandas_ta.ema(data['Close'],length=20)
  data['ema50']=pandas_ta.ema(data['Close'],length=50)
 
  #data['natr']=pandas_ta.natr(data['High'],data['Low'],data['Close'],length=10)
 
  psar=pandas_ta.psar(data['High'],data['Low'],data['Close'],0.4,0.4,0.4)
    
  psar['PSARl_0.4_0.4'].fillna(psar['PSARs_0.4_0.4'],inplace=True)
  data['psar']=psar['PSARl_0.4_0.4']
 
  psar=pandas_ta.psar(data['High'],data['Low'],data['Close'],2,2,2)
 
  psar['PSARl_2.0_2.0'].fillna(psar['PSARs_2.0_2.0'],inplace=True)
  data['stop_loss']=psar['PSARl_2.0_2.0']
 
  data['hbb']=ta.volatility.bollinger_hband(data['Close'])
  data['lbb']=ta.volatility.bollinger_lband(data['Close'])
     
  data['close_returns']=data.Close.pct_change(periods=1)
  data['price_roc']=data.Close.diff()
  data['vol_roc']=data.Volume.diff().ewm(span=10).mean()
 
  data['Volume'].iloc[:data['hma10'].isnull().sum()]=data['hma10'].iloc[:data['hma10'].isnull().sum()]
 
  data['vol_ema']=data['Volume'].ewm(span=10).mean()
  
  try:
    keltner=pandas_ta.kc(data['High'],data['Low'],data['Close'],scale=1.5,mamode='ema')
    keltner.columns=['lkeltner','mkeltner','hkeltner']
  
  except:
    keltner=pandas_ta.kc(data['High'],data['Low'],data['Close'],scale=1.5,mamode='ema',length=12)
    keltner.columns=['lkeltner','mkeltner','hkeltner']
    pass
 
  data=pd.concat([data,keltner],axis=1)
  
  data.columns=[col.lower() for col in data.columns]
 
  data['cci10']=pandas_ta.cci(data['low'],data['high'],data['close'],length=10)
  data['cci2']=pandas_ta.cci(data['low'],data['high'],data['close'],length=2)
 
  #data['qstick10']=pandas_ta.qstick(data['open'],data['close'],length=10)
  #data['qstick2']=pandas_ta.qstick(data['open'],data['close'],length=2)
 
  #data['kvo']=pandas_ta.kvo(data['high'],data['low'],data['close'],data['volume'],fast=20,long=50,length_sig=10)['KVOs_20_55_13']
  #data['eri']=pandas_ta.eri(data['high'],data['low'],data['close'],length=10)
  
  return data

def norm(x):
    
    nom = (x - x.min())*1.33
    denom = x.max() - x.min()
    return  nom/denom
 
def tanm(x):
  e=2.71828
  numerator=(e**(15*x)-e**(7.5))
  denominator=(e**(15*x)+e**(7.5))**-1
 
  if isinstance(x,float)==True:
    if np.isnan(numerator * denominator)==True:
      return 1
    
    else:
      return numerator*denominator
    
  else:
    return numerator*denominator
 
def as_currency(amount):
  
    if amount >= 0:
        return float('{:.2f}'.format(amount))
    else:
        return float('-{:.2f}'.format(-amount))

def conditional_order(ticker,size,stop_size,stop_price,TDSession,account_id,short=False,sell=False):
  
  size=abs(size)
  stop_size=abs(stop_size)
  ticker=ticker.upper()
 
  if not (short and sell):
    bid=TDSession.get_quotes([ticker])[ticker.upper()]['bidPrice']
    instruction='BUY'
    stop_instruction='SELL'
    stop_price=as_currency(stop_price if stop_price <bid else bid)
  
  elif short and not sell:
    ask=TDSession.get_quotes([ticker])[ticker.upper()]['askPrice']
    instruction='SELL_SHORT'
    stop_instruction='BUY_TO_COVER'
    stop_price=as_currency(stop_price if stop_price >ask else ask)
  
  elif not short and sell:
    bid=TDSession.get_quotes([ticker])[ticker.upper()]['bidPrice']
    instruction='SELL'
    stop_instruction='SELL'
    stop_price=as_currency(stop_price if stop_price >bid else bid)
  
  else:
    ask=TDSession.get_quotes([ticker])[ticker.upper()]['askPrice']
    instruction='BUY_TO_COVER'
    stop_instruction='BUY_TO_COVER'
    stop_price=as_currency(stop_price if stop_price >ask else ask)
    
  trigger_order={
    "orderStrategyType": "TRIGGER",
    "session": "NORMAL",
    'duration':'DAY',
    "orderType": "MARKET",
    "orderLegCollection": [
      {
        "instruction": instruction,
        "quantity": size,
        "instrument": {
          "assetType": "EQUITY",
          "symbol": ticker
        }
      }
    ],
    
    "childOrderStrategies": [
      {
 
        "orderStrategyType": "SINGLE",
        "session": "NORMAL",
        "duration": "GOOD_TILL_CANCEL",
        "orderType": "STOP",
        "stopPrice": stop_price,
        "orderLegCollection": [
          {
            "instruction": stop_instruction,
            "quantity": stop_size,
            "instrument": {
              "assetType": "EQUITY",
              "symbol": ticker
            }
          }
        ]
      }
    ]
  }
 
  TDSession.place_order(account_id,trigger_order)

def sell_all(already_dict,TDSession,account_id):
  
  for ticker in already_dict:
    try:
      if already_dict[ticker]>0:
        #order=market_order(ticker,already_dict[ticker],sell=True)
        
        order=sell_anytime(ticker,already_dict[ticker],TDSession,account_id)
       
        
      elif already_dict[ticker]<0:
        #order=market_order(ticker,already_dict[ticker],sell=True,short=True)
       
        order=sell_anytime(ticker,already_dict[ticker],TDSession,account_id,short=True)
        
      #TDSession.place_order(account=account_id,order=order)
    except Exception as e:
      print(e)
      print(ticker)
      pass

def sell_anytime(ticker,size,TDSession,account_id,short=False):
    
    ticker=ticker.upper()
    size=abs(size)
    quote=TDSession.get_quotes(instruments=[ticker])
      
    if short:
      instruction='BUY_TO_COVER'
      price=quote[ticker]['askPrice']+0.01
    
    else:
       instruction='SELL'
       price=quote[ticker]['bidPrice']-0.01
    
    price=as_currency(price)
    
    order={
    "orderType": "LIMIT",
    "session": 'SEAMLESS',
    "duration": "DAY",
    "price": price,
    "orderStrategyType": "SINGLE",
    "orderLegCollection": [
      {
        "instruction": instruction,
        "quantity": size,
        "instrument": {
          "symbol": ticker,
          "assetType": "EQUITY"
        }
      }
    ]
  }
     
    TDSession.place_order(account_id,order)

def buy_anytime(ticker,size,TDSession,account_id,short=False):
    
    ticker=ticker.upper()
    size=abs(size)
    quote=TDSession.get_quotes(instruments=[ticker])
    
      
    if short:
      instruction='SELL_SHORT'
      price=quote[ticker]['bidPrice']-0.01
    
    else:
       instruction='BUY'
       price=quote[ticker]['askPrice']+0.01
    
    price=as_currency(price)
 
    order={
    "orderType": "LIMIT",
    "session": 'SEAMLESS',
    "duration": "DAY",
    "price": price,
    "orderStrategyType": "SINGLE",
    "orderLegCollection": [
      {
        "instruction": instruction,
        "quantity": size,
        "instrument": {
          "symbol": ticker,
          "assetType": "EQUITY"
        }
      }
    ]
  }
    TDSession.place_order(account_id,order)


def cancel_orders(order_info,TDSession,account_id):
  filter=['CANCELED','REJECTED','EXPIRED']
  
  if 'orderStrategies' in order_info['securitiesAccount']:
    for order in order_info['securitiesAccount']['orderStrategies']:
      if order['status'] in filter:
        continue
      else:
        try:
          order_iterator(order,filter,TDSession,account_id)
        
        except Exception as e:
          print(e)
          pass

def order_iterator(order,filter,TDSession,account_id):
  
  if ('childOrderStrategies' in order) and (order['status']=='FILLED'):
    child_order=order['childOrderStrategies'][0]
    while (not child_order['cancelable']) and ('childOrderStrategies' in child_order):
      child_order=child_order['childOrderStrategies'][0]

    order=child_order
    
    if order['cancelable']:
      try:
        TDSession.cancel_order(account_id,order['orderId'])

      except Exception as e:
        print(e)
        pass
  
  elif order['status'] not in filter and (order['cancelable']):
    TDSession.cancel_order(account_id,order['orderId'])

def td_login():
    consumer_key='**********************'  
    callback_url='*******************'
    account_id = '********'          
    client_id=consumer_key
 
    TDSession = TDClient(
        client_id=client_id,
        redirect_uri=callback_url,
        credentials_path=r'C:\Users\Michael\creds.json' 
    )
 
    print(TDSession.login())
    return TDSession


def execute_brokerage():
  TDSession=td_login()

  account_id= '********'

  position_info=TDSession.get_accounts(account=account_id,fields=['positions'])
  order_info=TDSession.get_accounts(account=account_id,fields=['orders'])
  balances=order_info['securitiesAccount']['currentBalances']
  capital=balances['totalCash']*0.8

  tweets_df=get_tweets(accounts_list)
  tweets_df=Crypto_Fix(tweets_df)

  shares_dict=get_shares(tweets_df,capital,bl1=True)

  position_info=TDSession.get_accounts(account=account_id,fields=['positions'])
  order_info=TDSession.get_accounts(account=account_id,fields=['orders'])

  cancel_orders(order_info,TDSession,account_id)

  already_dict={}

  if 'positions' in position_info['securitiesAccount']:
    positions=position_info['securitiesAccount']['positions']
  
    for position in positions:
      
      ticker=position['instrument']['symbol'].lower() 

      size=position['longQuantity'] if position['longQuantity']>position['shortQuantity'] else -position['shortQuantity']
      already_dict[ticker]=size

    sell_all(already_dict,TDSession,account_id)

  for ticker in shares_dict:
    
    data=yahooTA(ticker,'1d')

    used_data=data[-90:]
    used_data.columns=[col.lower() for col in used_data.columns]


    std=pandas_ta.stdev(used_data['close'],length=2)
    std=norm(std[std<std.quantile(0.95)])
    factor=std.std()

    atr=pandas_ta.atr(used_data['high'],used_data['low'],used_data['close'],length=2).dropna()

    meany=atr.mean()

    y,x,_=plt.hist(atr)

    atr= (np.mean(int(x[np.where(y == y.max())][0]))+meany)/2

    reg_stop=data['close'].iloc[-1]*0.04

    if shares_dict[ticker]>0:
      stop_loss=data.close.iloc[-1]-max(0.01,as_currency(min(reg_stop,2.5*atr*factor)))
      conditional_order(ticker,abs(shares_dict[ticker]),abs(shares_dict[ticker]),stop_loss,TDSession,account_id)
    
    else:
      stop_loss=data.close.iloc[-1]+max(0.01,as_currency(min(reg_stop,2.5*atr*factor)))
      conditional_order(ticker,abs(shares_dict[ticker]),abs(shares_dict[ticker]),stop_loss,TDSession,account_id,short=True)
  
  
def get_tweets(accounts_list):
  dates=[]
  texts=[]
  authors=[]
  tickers=[]

  counter=0

  if datetime.datetime.now().weekday() >4:
    n=3
  else:
    n=1

  for id in accounts_list:

    end_date = datetime.datetime.utcnow() - datetime.timedelta(days=n)
    for status in Cursor(api.user_timeline, id=id,tweet_mode='extended',exclude_replies=True).items():
      if status.created_at < end_date:
        break

      counter+=2
      
      if counter>=5000:
        time.sleep(60*15)
        counter=0
      

      if hasattr(status, "entities"):
        entities = status.entities

        if "symbols" in entities and len(entities['symbols'])>0:
          for ent in entities['symbols']:
            if ent is not None:
              
              symbols=ent['text']
              tickers.append(symbols)
              num_id=status.id

              new_status=api.get_status(num_id,tweet_mode='extended')

              if hasattr(new_status,'full_text'):
                texts.append(new_status.full_text.replace('\n'," "))
              else:
                  texts.append(status.text.replace('\n'," "))
          
              dates.append(status.created_at)
              authors.append(status.author.screen_name)

      
  tweet_df=pd.DataFrame()
  tweet_df['dates']=dates
  tweet_df['texts']=texts
  tweet_df['authors']=authors
  tweet_df['tickers']=tickers
  tweet_df['sent_scores']=[SIA().polarity_scores(comment_body)['compound'] for comment_body in tweet_df['texts']]
  tweet_df=tweet_df[tweet_df['sent_scores']!=0]
  tweet_df=tweet_df.drop_duplicates()
  tweet_df=tweet_df.sort_values('dates')
  tweet_df['dates']=[str(date)[:10] for date in tweet_df['dates']]

  for i in tweet_df['tickers'].unique():
    if len(tweet_df[tweet_df['tickers']==i])<3 or len(tweet_df['authors'][tweet_df['tickers']==i].unique())<3:
      tweet_df=tweet_df[tweet_df['tickers']!=i]
  
  return tweet_df

execute_brokerage()