Matrix profiles provide a computationally efficient method of calculating similarities between sequences of different lengths within a timeseries. I wanted to play around with
using this concept, by trying to find motifs not just within a stock's own timeseries, but comparatively to the timeseries of stocks cointegrated with it. I used a rough least-squares 
regression to find the top subset of sequences similar to that of the stock price being forecasted, with their next-day prices as predictions(this was applied to stock volumes too. Additionally, I calculated confidence interval
calculations to aid in possible position sizing given these predictions. 
