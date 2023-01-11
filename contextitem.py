# -*- coding: utf-8 -*-

import sys
import xbmc

def main():
    arg = sys.argv[1]
    if arg == 'folder':
        folder = xbmc.getInfoLabel('ListItem.folderPath')
        xbmc.executebuiltin('RecursiveSlideShow(\"%s\")' % folder)

if __name__ == '__main__':
    main()