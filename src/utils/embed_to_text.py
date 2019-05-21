from discord import Embed


def make_full_embed(e: Embed):
    if not e.author.name:
        e.set_author(name='')
    if not e.title:
        e.title = ''
    if not e.description:
        e.description = ''
    if not e.footer.text:
        e.set_footer(text='')

    return e


def embed_to_text(e: Embed):
    ''' Return all embed's visible text. '''
    e = make_full_embed(e)

    _str = ''

    _str += e.author.name + '\n'
    _str += e.title + '\n'
    _str += e.description + '\n'

    for f in e.fields:
        _str += f.name + ':' + f.value + ';'
    _str += '\n'

    _str += e.footer.text

    return _str


if __name__ == "__main__":
    _e = Embed(title='Title', description='Description')
    _e.set_author(name='Author')
    _e.add_field(name='Name1', value='Value1')
    _e.add_field(name='Name2', value='Value2')
    _e.set_footer(text='Footer')

    _target = ('Author\n'
               'Title\n'
               'Description\n'
               'Name1:Value1;Name2:Value2;\n'
               'Footer')

    # print(embed_to_text(_e))
    assert embed_to_text(_e) == _target