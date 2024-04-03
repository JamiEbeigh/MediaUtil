
import math
from token import PERCENT


def printProgress( message, completed, total, barLen=20, messagePad=20, padChar='.' ):
  #'█' '▓' '▒' '░'

  percentage = completed / total

  blockCount = barLen * percentage 

  solidBlocks = math.floor( blockCount )
  remainder = blockCount - solidBlocks
  lastBlock = '▓' if remainder > 0.75 else '▒' if remainder > 0.5 else '░' if remainder > 0.25 else ' ' 
  
  blockTxt = '█' * solidBlocks + lastBlock + ' ' * (barLen - solidBlocks - 1)

  print( 
    message + padChar * (messagePad - len(message)),
    F'[{blockTxt}]',
    F'({completed}/{total} - {percentage:.1%})',
    end='\r')

  if completed == total:
    print()
