class Solution(object):
    def singleNumber(self, nums):
        """
        :type nums: List[int]
        :rtype: int
        """
        return reduce(lambda x,y:x^y,nums)

print(Solution().singleNumber([4,1,2,1,2]))
