class Solution(object):
    def twoSum(self, nums, target):
        """
        :type nums: List[int]
        :type target: int
        :rtype: List[int]
        """

        dictS = dict()
        for i, v in enumerate(nums):
            if not dictS.get(v):
                dictS[v] = [i, ]
            else:
                dictS[v].append(i)
        for i, num in enumerate(nums):
            if target - num in dictS:
                for j, index in enumerate(dictS[target - num]):
                    if index != i: return [index, i]


print(Solution().twoSum(
    [3, 3], 6))
