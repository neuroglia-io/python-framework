from abc import ABC, abstractclassmethod


class LoggerBase(ABC):
        
    @abstractclassmethod
    def log(text: str):
        raise NotImplementedError()
        
class PrintLogger(LoggerBase):
        
    def log(text: str):
        print(text)
        
class FileLogger(LoggerBase):
    
    def log(text: str):
        with open('example.txt', 'a') as file:
            file.write(f'{text}\n')
            
class NullLogger(LoggerBase):
        
    def log(text: str):
        pass