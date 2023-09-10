import string


class Template(string.Template):
    """
    Adds a partial() method to string.Template that returns a Template with some results filled in.

    Also ensures that all templates end in at least one space.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.template[-1] == " ", self.template
        # Don't use a straight single quote--it looks unprofessional. Instead,
        # use ‘ or ’.
        assert "'" not in self.template, self.template

    def partial(self, *args, **kwargs):
        return Template(self.safe_substitute(*args, **kwargs))

    def __repr__(self):
        module = type(self).__module__
        qualname = type(self).__qualname__
        return f"<{module}.{qualname} object at {hex(id(self))} template='{self.template}'>"

    def __add__(self, other):
        if isinstance(other, str):
            return Template(self.template + other)

        elif isinstance(other, self.__class__):
            return Template(self.template + other.template)
