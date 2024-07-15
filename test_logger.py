from logger import ColoredLogger

# Create an instance of ColoredLogger with a name (usually __name__)
logger = ColoredLogger(__name__)

def main():
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

if __name__ == "__main__":
    main()
