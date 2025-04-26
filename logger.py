from datetime import datetime

class Logger:
    def __init__(self, name: str = "TabWizard"):
        self.name = name

    def _current_timestamp(self) -> str:
        now = datetime.now()
        return now.strftime('%H:%M:%S.%f')[:-3]  # Hours:Minutes:Seconds:Milliseconds

    def _format_message(self, level: str, message: str) -> str:
        timestamp = self._current_timestamp()
        return f"[{timestamp}] [{self.name}] [{level.upper()}] {message}"

    def debug(self, message: str):
        print(self._format_message("DEBUG", message))

    def info(self, message: str):
        print(self._format_message("INFO", message))

    def error(self, message: str):
        print(self._format_message("ERROR", message))
        
    def warning(self, message: str):
        print(self._format_message("WARNING", message))
