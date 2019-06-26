from datetime import datetime

def relevant_weekday_index() -> int:
    '''
    Get the weekday with the respect to the current hour.

    If the hour is greater than 12, get the weekday index corresponding
    tomorrow.

    Return:
        Int representing the weekday index.
    '''

    return datetime.today().weekday() + (datetime.now().hour > 12)


if __name__ == "__main__":
    print(relevant_weekday_index())