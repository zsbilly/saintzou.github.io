class Solution(object):
    def isValidSudoku(self, board):
        """
        :type board: List[List[str]]
        :rtype: bool
        """
        for row in board:
            if len(set(row))+row.count('.')-1!=len(row):
                return False
        for col in [[row[i] for row in board] for i in range(0,len(board))]:
            if len(set(col))+col.count('.')-1!=len(col):
                return False
        ## 我觉得我对block的遍历方式还是蛮吊的！
        for block in [[row[i] for row in board[m:m+3] for i in range(n,n+3)] for m in range(0,7,3) for n in range(0,7,3)]:
            if len(set(block))+block.count('.')-1!=len(block):
                return False

        return True



print( Solution().isValidSudoku([
  ["5","3",".",".","7",".",".",".","."],
  ["6",".",".","1","9","5",".",".","."],
  [".","9","8",".",".",".",".","6","."],
  ["8",".",".",".","6",".",".",".","3"],
  ["4",".",".","8",".","3",".",".","1"],
  ["7",".",".",".","2",".",".",".","6"],
  [".","6",".",".",".",".","2","8","."],
  [".",".",".","4","1","9",".",".","5"],
  [".",".",".",".","8",".",".","7","9"]
]))
