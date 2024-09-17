import typing

def is_str_list(val: list[typing.Any]) -> typing.TypeGuard[list[str]]:  
    """Determines whether all objects in the list are strings"""  
    return all(isinstance(x, str) for x in val)
