# Comes from:
# https://github.com/python/cpython/commit/2d6097d027e0dd3debbabc702aa9c98d94ba32a3

from docutils import nodes
from docutils.parsers.rst import Directive


class Availability(Directive):

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self):
        pnode = nodes.paragraph(classes=["availability"])
        n, m = self.state.inline_text(
            ":ref:`Availability <availability>`: ", self.lineno
        )
        pnode.extend(n + m)
        n, m = self.state.inline_text(self.arguments[0], self.lineno)
        pnode.extend(n + m)
        return [pnode]


def setup(app):
    app.add_directive("availability", Availability)

    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
