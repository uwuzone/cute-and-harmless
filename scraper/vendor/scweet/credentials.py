class Credentials:
    username: str
    password: str


    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password