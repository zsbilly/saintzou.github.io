class Solution(object):
    def firstUniqChar(self, s):
        """
        :type s: str
        :rtype: int
        """
        dictS = dict()
        for i in s:
            dictS[i] = dictS[i] + 1 if dictS.get(i) else 1
        for i, v in enumerate(list(s)):
            if v in dictS and dictS[v] == 1:
                return i
        return -1

print(Solution().firstUniqChar('leetcode'))

# 这个罗列所有字符的解法值得借鉴
# class Solution(object):
#     def firstUniqChar(self, s):
#         """
#         :type s: str
#         :rtype: int
#         """
#         letters='abcdefghijklmnopqrstuvwxyz'
#         index=[s.index(l) for l in letters if s.count(l) == 1]
#         return min(index) if len(index) > 0 else -1
#         #return min([s.find(c) for c in string.ascii_lowercase if s.count(c)==1] or [-1])
