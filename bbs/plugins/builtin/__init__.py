"""
Built-in Plugins Package

This package contains the built-in plugins that come with the BBS.

Plugins:
    - PersonalMessaging: Personal message commands (MSG, READ, DELETE)
    - BulletinBoard: BBS commands (BBS, AREAS, READ area)
    - Admin: Admin commands (ADMIN CREATE/DELETE/LIST)
"""

from bbs.plugins.builtin.PersonalMessaging import PersonalMessagingPlugin
from bbs.plugins.builtin.BulletinBoard import BulletinBoardPlugin
from bbs.plugins.builtin.Admin import AdminPlugin

__all__ = [
    'PersonalMessagingPlugin',
    'BulletinBoardPlugin',
    'AdminPlugin',
]
