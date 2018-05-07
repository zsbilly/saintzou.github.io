class Solution(object):
    def removeDuplicates(self, nums):
        """
        :type nums: List[int]
        :rtype: int
        """
        if len(nums)==0: return 0
        j = 0
        for i, v in enumerate(nums):
            if i != j and v != nums[j]:
                j += 1
                nums[i], nums[j] = nums[j], nums[i]
                i += 1
        return j+1


print(Solution().removeDuplicates([]))
