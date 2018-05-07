# -*- coding: utf-8 -*
class Solution(object):
    def intersect(self, nums1, nums2):
        """
        :type nums1: List[int]
        :type nums2: List[int]
        :rtype: List[int]
        """
        res = []
        dict1 = dict()
        for i in nums1:
            dict1[i] = dict1[i] + 1 if dict1.get(i) else 1
        for j in nums2:
            if j in dict1 and dict1[j] != 0:
                dict1[j] -= 1
                res.append(j)
        return res


print(Solution().intersect( [2, 2,2,2,2],[]))

# 如果给定的数组已经排好序呢？你将如何优化你的算法？
# 排好序的情况下可以采用two pointers省空间

# 如果 nums1 的大小比 nums2 小很多，哪种方法更优？
# hash nums1

# 如果nums2的元素存储在磁盘上，内存是有限的，你不能一次加载所有的元素到内存中，你该怎么办？
# hash nums1，去磁盘上逐个比对nums2
