import PyQt6
from PyQt6.QtWidgets import QApplication
import sys
import asyncio
import qasync
from qasync import QApplication
from .main_window import MainWindow
from ..core.settings import Settings
from ..features.controllers import MainController

class App:
    def __init__(self):
        # Initialize Qt Application
        self.app = QApplication(sys.argv)
        self.event_loop = None
        
        # Initialize core components
        self.settings = Settings()
        
        # Initialize controller
        # self.controller = MainController(self.settings)
        
        # Initialize main window
        # self.window = MainWindow(self.controller)

    def run(self):
        """Run the application."""
        self.event_loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(self.event_loop)

        # 이제 event_loop가 있으니 Controller 생성 가능
        self.controller = MainController(self.settings, self.event_loop) 
        self.window = MainWindow(self.controller)
        
        self.window.show()
        
        exit_code = 0
        try:
            self.event_loop.run_forever()
        except KeyboardInterrupt:
            print("Application interrupted. Shutting down...")
        finally:
            print("Cleaning up asyncio tasks...")
            tasks = asyncio.all_tasks(loop=self.event_loop)
            for task in tasks:
                if task is not asyncio.current_task(loop=self.event_loop):
                    task.cancel()
            
            async def wait_for_tasks_cancellation():
                await asyncio.gather(*[t for t in tasks if t is not asyncio.current_task(loop=self.event_loop)], return_exceptions=True)

            if tasks:
                self.event_loop.run_until_complete(wait_for_tasks_cancellation())

            if hasattr(self.event_loop, 'shutdown_asyncgens'):
                self.event_loop.run_until_complete(self.event_loop.shutdown_asyncgens())
            
            self.event_loop.close()
            print("Asyncio event loop closed.")

        return 0 