class Solution(object):
    def rotate(self, matrix):
        """
        :type matrix: List[List[int]]
        :rtype: void Do not return anything, modify matrix in-place instead.
        """
        for row in matrix:
            row.reverse()
        for i in range(0,len(matrix)-1):
            for j in range(len(matrix)-1-i,-1,-1):
                matrix[i][j],matrix[len(matrix)-j-1][len(matrix)-i-1]=matrix[len(matrix)-j-1][len(matrix)-i-1],matrix[i][j]

        return matrix
print( Solution().rotate([
  [1,2,3],
  [4,5,6],
  [7,8,9]
],))

