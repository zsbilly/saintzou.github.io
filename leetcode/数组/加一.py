class Solution(object):
    def plusOne(self, digits):
        """
        :type digits: List[int]
        :rtype: List[int]
        """
        converted = int(''.join(map(str,digits)))
        converted += 1
        return map(int, list(str(converted)))


print(Solution().plusOne([4, 3, 2, 1]))
