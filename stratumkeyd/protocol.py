'''
Created on 25.08.2012

@author: oni
'''


class modify_command:
    def __init__(self,command,id,key):
        self.command=command
        self.id=id
        self.key=key
   
class response:
    def __init__(self,command,result):
        self.command=command
        self.result=result

class log_command:
    def __init__(self,command):
        self.command=command

