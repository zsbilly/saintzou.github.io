# -*- coding: utf-8 -*
class Solution(object):
    def rotate(self, nums, k):
        """
        :type nums: List[int]
        :type k: int
        :rtype: void Do not return anything, modify nums in-place instead.
        """
        if len(nums)==0:return
        k=k%len(nums) ## 别忘了计算余数！！！！
        nums.reverse()
        nums[0:k]=list(reversed(nums[0:k]))
        nums[k:]= list(reversed( nums[k:]))
        print(nums)

print(Solution().rotate([1,2,3], 4))
