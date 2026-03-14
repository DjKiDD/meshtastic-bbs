"""
Built-in Plugins Package

This package contains the built-in plugins that come with the BBS.

Plugins:
    - PersonalMessaging: Personal message commands (MSG, READ, DELETE)
    - BulletinBoard: BBS commands (BBS, AREAS, READ area)
"""

from bbs.plugins.builtin.PersonalMessaging import PersonalMessagingPlugin
from bbs.plugins.builtin.BulletinBoard import BulletinBoardPlugin

__all__ = [
    'PersonalMessagingPlugin',
    'BulletinBoardPlugin',
]
