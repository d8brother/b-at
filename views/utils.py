# -*- coding: utf-8 -*-
import os
import re
import main
import jinja2
import urllib2
from pyatom import AtomFeed
from google.appengine.api import users
from models import WikiPage, UserPreferences, get_cur_user


JINJA = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


def format_short_datetime(value):
    if value is None:
        return ''
    return value.strftime('%m-%d %H:%M')


def format_datetime(value):
    if value is None:
        return ''
    return value.strftime('%Y-%m-%d %H:%M:%S')


def format_iso_datetime(value):
    if value is None:
        return ''
    return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def to_path(title):
    return '/' + WikiPage.title_to_path(title)


def to_rel_path(title):
    return WikiPage.title_to_path(title)


def to_pluspath(title):
    return '/%2B' + WikiPage.title_to_path(title)


def urlencode(s):
    return urllib2.quote(s.encode('utf-8'))


def userpage_link(user):
    if user is None:
        return '<span class="user">Anonymous</span>'
    else:
        email = user.email()
        preferences = UserPreferences.get_by_email(email)

        if preferences is None:
            return '<span class="user email">%s</span>' % email
        elif preferences.userpage_title is None or len(preferences.userpage_title.strip()) == 0:
            return '<span class="user email">%s</span>' % email
        else:
            path = to_path(preferences.userpage_title)
            return '<a href="%s" class="user userpage wikilink">%s</a>' % (path, preferences.userpage_title)


def has_supported_language(hashbangs):
    config = WikiPage.get_config()
    return any(x in config['highlight']['supported_languages'] for x in hashbangs)


JINJA.filters['dt'] = format_datetime
JINJA.filters['sdt'] = format_short_datetime
JINJA.filters['isodt'] = format_iso_datetime
JINJA.filters['to_path'] = to_path
JINJA.filters['to_rel_path'] = to_rel_path
JINJA.filters['to_pluspath'] = to_pluspath
JINJA.filters['userpage'] = userpage_link
JINJA.filters['has_supported_language'] = has_supported_language


def render_posts_atom(req, title, pages):
    host = req.host_url
    config = WikiPage.get_config()
    if title is None:
        feed_title = '%s: posts' % config['service']['title']
        url = "%s/sp.posts?_type=atom" % host
    else:
        feed_title = title
        url = "%s/%s?_type=atom" % (WikiPage.title_to_path(title), host)

    feed = AtomFeed(title=feed_title,
                    feed_url=url,
                    url="%s/" % host,
                    author=config['admin']['email'])
    for page in pages:
        feed.add(title=page.title,
                 content_type="html",
                 content=page.rendered_body,
                 author=page.modifier,
                 url='%s%s' % (host, page.absolute_url),
                 updated=page.published_at)
    return feed.to_string()


def get_restype(req, default):
    return str(req.GET.get('_type', default))


def set_response_body(res, resbody, head):
    if head:
        res.headers['Content-Length'] = str(len(resbody))
    else:
        res.write(resbody)


def template(req, path, data):
    t = JINJA.get_template('templates/%s' % path)
    config = WikiPage.get_config()

    user = get_cur_user()
    preferences = None
    if user is not None:
        preferences = UserPreferences.get_by_email(user.email())

    data['is_local'] = req.host_url.startswith('http://localhost')
    data['is_mobile'] = is_mobile(req)
    data['user'] = user
    data['preferences'] = preferences
    data['users'] = users
    data['cur_url'] = req.url
    data['config'] = config
    data['app'] = {
        'version': main.VERSION,
    }
    return t.render(data)


def is_mobile(req):
    p = r'.*(Android|Fennec|GoBrowser|iPad|iPhone|iPod|Mobile|Opera Mini|Opera Mobi|Windows CE).*'
    if 'User-Agent' not in req.headers:
        return False
    return re.match(p, req.headers['User-Agent']) is not None


def obj_to_html(o, key=None):
    obj_type = type(o)
    if isinstance(o, dict):
        return render_dict(o)
    elif obj_type == list:
        return render_list(o)
    elif obj_type == str or obj_type == unicode:
        if key is not None and key == 'schema':
            return o
        else:
            return '<a href="%s">%s</a>' % (to_path(o), o)
    else:
        return str(o)


def render_dict(o):
    if len(o) == 1:
        return obj_to_html(o.values()[0])
    else:
        html = ['<dl class="wq wq-dict">']
        for key, value in o.items():
            html.append('<dt class="wq-key-%s">' % key)
            html.append(key)
            html.append('</dt>')
            html.append('<dd class="wq-value-%s">' % key)
            html.append(obj_to_html(value, key))
            html.append('</dd>')
        html.append('</dl>')

        return '\n'.join(html)


def render_list(o):
    html = ['<ul class="wq wq-list">']
    for value in o:
        html.append('<li>')
        html.append(obj_to_html(value))
        html.append('</li>')
    html.append('</ul>')

    return '\n'.join(html)
