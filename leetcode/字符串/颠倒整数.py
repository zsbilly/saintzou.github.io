# -*- coding: UTF-8 -*-
class Solution(object):
    def reverse(self, x):
        """
        :type x: int
        :rtype: int
        """
        res = 0
        maxStr = str(2 ** 31 - 1)
        minStr = str(-(2 ** 31))
        stred = str(x)
        if stred[0] == '-':
            cmped = '-' + '0'*(len(minStr)-len(stred[::-1])) + stred[:0:-1]
            if cmped <= minStr:
                res = int(cmped)
        else:
            cmped='0'*(len(maxStr)-len(stred[::-1]))+stred[::-1]
            if cmped<=maxStr:
                res= int(cmped)
        return res

print(Solution().reverse(-563847412))


# 我认为这题提交的解法里很多都是扯淡，比如下面这个，x = int(x)这个就默认了在系统内本身就支持32位以上的有符号整数，
# 对于那些32位的系统而言，这种方法是不奏效的，所以整体思路应该就是基于字符串的比较而不是基于数值本身的比较。
# 像下面这种答案，写了跟没写一样
# class  SolutionSolution(object)(object)::
#          defdef  reversereverse(self, x)(self, x)::
#                  """
#         :type x: int
#         :rtype: int
#         """"""         :ty
#         if x>=0:
#             rx = str(x)
#             x = rx[::-1]
#             x = int(x)
#             if x>(2**31-1):
#                 return 0
#             else:
#                 return x
#         else:
#             rx = str(x)
#             rx = rx[1:]
#             x=rx[::-1]
#             x = int(x)
#             x=-x
#             if x<(-(2)**31):
#                 return 0
#             else:
#                 return x
