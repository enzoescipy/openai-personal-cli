import PyQt6
from PyQt6.QtWidgets import QApplication
import sys
import asyncio
import qasync
from .main_window import MainWindow
from ..core.settings import Settings
from ..features.controllers import MainController

class App:
    def __init__(self):
        # Initialize Qt Application
        self.app = QApplication(sys.argv)
        
        # Initialize core components
        self.settings = Settings()
        
        # Initialize controller
        self.controller = MainController(self.settings)
        
        # Initialize main window
        self.window = MainWindow(self.controller)

    def run(self):
        """Run the application."""
        loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(loop)

        self.window.show()
        
        exit_code = 0
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print("Application interrupted. Shutting down...")
        finally:
            print("Cleaning up asyncio tasks...")
            tasks = asyncio.all_tasks(loop=loop)
            for task in tasks:
                if task is not asyncio.current_task(loop=loop):
                    task.cancel()
            
            async def wait_for_tasks_cancellation():
                await asyncio.gather(*[t for t in tasks if t is not asyncio.current_task(loop=loop)], return_exceptions=True)

            if tasks:
                loop.run_until_complete(wait_for_tasks_cancellation())

            if hasattr(loop, 'shutdown_asyncgens'):
                loop.run_until_complete(loop.shutdown_asyncgens())
            
            loop.close()
            print("Asyncio event loop closed.")

        return 0 