from src.gui import InterviewGUI
from loguru import logger

def main():
    logger.add("app.log")
    app = InterviewGUI()
    app.run()

if __name__ == "__main__":
    main()
