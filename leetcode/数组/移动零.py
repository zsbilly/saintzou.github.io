# -*- coding: utf-8 -*
class Solution(object):
    def moveZeroes(self, nums):
        """
        :type nums: List[int]
        :rtype: void Do not return anything, modify nums in-place instead.
        """
        i, j = 0, 0
        while j < len(nums) and i<len(nums):
            j=max(i,j) ## 还是要注意细节！！！ j在这里只能比i大，这是最初算法设计时就考虑到的，不应该随便舍弃
            if nums[j] == 0:
                j += 1
            elif nums[j] != 0 and nums[i]==0:
                nums[i], nums[j] = nums[j], nums[i]
                i += 1
                j += 1
            else:
                i += 1
        print(nums)


print(Solution().moveZeroes([1,0,0]))
