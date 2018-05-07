class Solution(object):
    def maxProfit(self, prices):
        """
        :type prices: List[int]
        :rtype: int
        """
        if len(prices)<2 :return 0
        maxprofit = 0
        for i in range(0,len(prices)-1):
            gap=prices[i+1]-prices[i]
            if(gap>0):maxprofit+=gap;
        return maxprofit

print(Solution().maxProfit([1,6,4,3,1]))
