class Annotation(object):
    def is_empty(self):
        return len(self.sources) == 0
