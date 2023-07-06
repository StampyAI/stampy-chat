import sys
from pathlib import Path
sys.path = [str(Path(__file__).parent.parent)] + sys.path
from env import PINECONE_INDEX

from chat import talk_to_robot_simple, set_debug_print

set_debug_print(False)
print(talk_to_robot_simple(PINECONE_INDEX, 'Hello.', log = lambda x: None))
