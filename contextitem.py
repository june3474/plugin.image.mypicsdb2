# -*- coding: utf-8 -*-

import sys
import xbmc

def main():
    if sys.argv[1] == 'folder':
        folder = xbmc.getInfoLabel('ListItem.folderPath')
        xbmc.executebuiltin('RecursiveSlideShow(\"%s\")' % folder)
        
    if sys.argv[1] == 'picture':
        folder = xbmc.getInfoLabel('ListItem.folderPath')
        filepath = xbmc.getInfoLabel('ListItem.FileNameAndPath')
        xbmc.executebuiltin('SlideShow(\"%s\", recursive, \
                             beginslide=\"%s\")' % (folder, filepath))        

if __name__ == '__main__':
    main()