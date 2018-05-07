class Solution(object):
    def containsDuplicate(self, nums):
        """
        :type nums: List[int]
        :rtype: bool
        """
        dictS = dict()
        for i in nums:
            if dictS.get(i):
                return True
            else:
                dictS[i] = 1
        return False


print(Solution().containsDuplicate([1,3,3,1]))
