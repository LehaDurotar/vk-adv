class ResponseError(Exception):
    def __init__(self):
        Exception.__init__(self, 'Some connection error!')


class AppScopeError(Exception):
    def __init__(self):
        Exception.__init__(self, 'Some error with vk ap permission!')
