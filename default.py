#!/usr/bin/python
# -*- coding: utf-8 -*-

__addonname__ = 'plugin.image.mypicsdb2'

import mypicsdb.viewer as viewer
import mypicsdb.translationeditor as translationeditor
import mypicsdb.googlemaps as googlemaps
import mypicsdb.filterwizard as filterwizard
import mypicsdb.MypicsDB as MypicsDB
# common depends on __addonname__
import mypicsdb.common as common

import os
import sys
import time
import re
import urllib

from os.path import join, isfile, basename, dirname, splitext, exists
from urllib.parse import parse_qsl, unquote, quote
from time import strftime, strptime
from traceback import print_exc
from ast import Not

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs


# MikeBZH44
try:
    import json as simplejson
    # test json has not loads, call error
    if not hasattr(simplejson, "loads"):
        raise Exception("Hmmm! Error with json %r" % dir(simplejson))
except Exception as e:
    print("[MyPicsDB] %s" % str(e))
    import simplejson

# MikeBZH44: commoncache for MyPicsDB with 1 hour timeout
try:
    import mypicsdb.StorageServer as StorageServer
except:
    import mypicsdb.storageserverdummy as StorageServer

# set variables used by other modules
sys_encoding = sys.getfilesystemencoding()

if "MypicsDB" in sys.modules:
    del sys.modules["MypicsDB"]

# these few lines are taken from AppleMovieTrailers script
# Shared resources
home = common.getaddon_path()
BASE_RESOURCE_PATH = join(home, "resources")
DATA_PATH = common.getaddon_info('profile')
PIC_PATH = join(BASE_RESOURCE_PATH, "images")

# catching the OS :
#   win32 -> win
#   darwin -> mac
#   linux -> linux
RunningOS = sys.platform

cache = StorageServer.StorageServer("MyPicsDB", 1)

files_fields_description = {
    "strFilename": common.getstring(30300),
    "strPath": common.getstring(30301),
    "Thumb": common.getstring(30302),
}


class _Info:
    def __init__(self, params):
        _args = parse_qsl(params, separator=',')
        self.__dict__.update(_args)

    def has_key(self, key):
        return key in self.__dict__

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __str__(self):
        return str(self.__class__) + '\n' + \
            '\n'.join(('{} = {}'.format(item, self.__dict__[item]) for item in self.__dict__))

    def output(self):
        common.log("_Info", str(self.__class__) + '\n' + \
            '\n'.join(('{} = {}'.format(item, self.__dict__[item]) for item in self.__dict__)))


global MPDB


class Main:
    def __init__(self):
        try:
            MPDB = MypicsDB.MyPictureDB()
        except Exception as msg:
            common.log("Main.__init__", "%s - %s" % (Exception, str(msg)), xbmc.LOGERROR)
            raise msg

        self.get_args()

    def get_args(self):
        common.log("Main.get_args", 'MyPicturesDB plugin called with "%s".' % sys.argv[2][1:], xbmc.LOGINFO)

        self.parm = unquote(sys.argv[2]).replace("\\\\", "\\")
        # change for ruuk's plugin screensaver
        self.parm = self.parm.replace('&plugin_slideshow_ss=true', '')

        # for peppe_sr due to his used skin widget plugin
        p = re.compile('&reload=[^&]*')
        self.parm = p.sub('', self.parm)

        sys.argv[2] = self.parm
        self.parm = self.cleanup(self.parm[1:])
        self.args = _Info(self.parm)

        if not hasattr(self.args, 'page'):
            self.args.page = 0

    def cleanup(self, parm):
        in_apostrophe = False
        prev_char = ""
        prevprev_char = ""
        output = ""

        for char in parm:
            if (char == "'" and prev_char != "\\") or \
               (char == "'" and prev_char == "\\" and prevprev_char == "\\"):
                if not in_apostrophe:
                    in_apostrophe = True
                else:
                    in_apostrophe = False
            if char == "&" and not in_apostrophe:
                char = ","

            output += char

            prevprev_char = prev_char
            prev_char = char
            if prevprev_char == "\\" and prev_char == "\\":
                prev_char = ""
                prevprev_char = ""

        return output

    def is_picture(self, filename):
        ext = splitext(filename)[1][1:].upper()
        return ext in [ext.upper() for ext in common.getaddon_setting("picsext").split("|")]

    def is_video(self, filename):
        ext = splitext(filename)[1][1:].upper()
        return ext in [ext.upper() for ext in common.getaddon_setting("vidsext").split("|")]

    def calc_crc(self, url):
        CRC_TAB = [
            0x00000000, 0x04C11DB7, 0x09823B6E, 0x0D4326D9,
            0x130476DC, 0x17C56B6B, 0x1A864DB2, 0x1E475005,
            0x2608EDB8, 0x22C9F00F, 0x2F8AD6D6, 0x2B4BCB61,
            0x350C9B64, 0x31CD86D3, 0x3C8EA00A, 0x384FBDBD,
            0x4C11DB70, 0x48D0C6C7, 0x4593E01E, 0x4152FDA9,
            0x5F15ADAC, 0x5BD4B01B, 0x569796C2, 0x52568B75,
            0x6A1936C8, 0x6ED82B7F, 0x639B0DA6, 0x675A1011,
            0x791D4014, 0x7DDC5DA3, 0x709F7B7A, 0x745E66CD,
            0x9823B6E0, 0x9CE2AB57, 0x91A18D8E, 0x95609039,
            0x8B27C03C, 0x8FE6DD8B, 0x82A5FB52, 0x8664E6E5,
            0xBE2B5B58, 0xBAEA46EF, 0xB7A96036, 0xB3687D81,
            0xAD2F2D84, 0xA9EE3033, 0xA4AD16EA, 0xA06C0B5D,
            0xD4326D90, 0xD0F37027, 0xDDB056FE, 0xD9714B49,
            0xC7361B4C, 0xC3F706FB, 0xCEB42022, 0xCA753D95,
            0xF23A8028, 0xF6FB9D9F, 0xFBB8BB46, 0xFF79A6F1,
            0xE13EF6F4, 0xE5FFEB43, 0xE8BCCD9A, 0xEC7DD02D,
            0x34867077, 0x30476DC0, 0x3D044B19, 0x39C556AE,
            0x278206AB, 0x23431B1C, 0x2E003DC5, 0x2AC12072,
            0x128E9DCF, 0x164F8078, 0x1B0CA6A1, 0x1FCDBB16,
            0x018AEB13, 0x054BF6A4, 0x0808D07D, 0x0CC9CDCA,
            0x7897AB07, 0x7C56B6B0, 0x71159069, 0x75D48DDE,
            0x6B93DDDB, 0x6F52C06C, 0x6211E6B5, 0x66D0FB02,
            0x5E9F46BF, 0x5A5E5B08, 0x571D7DD1, 0x53DC6066,
            0x4D9B3063, 0x495A2DD4, 0x44190B0D, 0x40D816BA,
            0xACA5C697, 0xA864DB20, 0xA527FDF9, 0xA1E6E04E,
            0xBFA1B04B, 0xBB60ADFC, 0xB6238B25, 0xB2E29692,
            0x8AAD2B2F, 0x8E6C3698, 0x832F1041, 0x87EE0DF6,
            0x99A95DF3, 0x9D684044, 0x902B669D, 0x94EA7B2A,
            0xE0B41DE7, 0xE4750050, 0xE9362689, 0xEDF73B3E,
            0xF3B06B3B, 0xF771768C, 0xFA325055, 0xFEF34DE2,
            0xC6BCF05F, 0xC27DEDE8, 0xCF3ECB31, 0xCBFFD686,
            0xD5B88683, 0xD1799B34, 0xDC3ABDED, 0xD8FBA05A,
            0x690CE0EE, 0x6DCDFD59, 0x608EDB80, 0x644FC637,
            0x7A089632, 0x7EC98B85, 0x738AAD5C, 0x774BB0EB,
            0x4F040D56, 0x4BC510E1, 0x46863638, 0x42472B8F,
            0x5C007B8A, 0x58C1663D, 0x558240E4, 0x51435D53,
            0x251D3B9E, 0x21DC2629, 0x2C9F00F0, 0x285E1D47,
            0x36194D42, 0x32D850F5, 0x3F9B762C, 0x3B5A6B9B,
            0x0315D626, 0x07D4CB91, 0x0A97ED48, 0x0E56F0FF,
            0x1011A0FA, 0x14D0BD4D, 0x19939B94, 0x1D528623,
            0xF12F560E, 0xF5EE4BB9, 0xF8AD6D60, 0xFC6C70D7,
            0xE22B20D2, 0xE6EA3D65, 0xEBA91BBC, 0xEF68060B,
            0xD727BBB6, 0xD3E6A601, 0xDEA580D8, 0xDA649D6F,
            0xC423CD6A, 0xC0E2D0DD, 0xCDA1F604, 0xC960EBB3,
            0xBD3E8D7E, 0xB9FF90C9, 0xB4BCB610, 0xB07DABA7,
            0xAE3AFBA2, 0xAAFBE615, 0xA7B8C0CC, 0xA379DD7B,
            0x9B3660C6, 0x9FF77D71, 0x92B45BA8, 0x9675461F,
            0x8832161A, 0x8CF30BAD, 0x81B02D74, 0x857130C3,
            0x5D8A9099, 0x594B8D2E, 0x5408ABF7, 0x50C9B640,
            0x4E8EE645, 0x4A4FFBF2, 0x470CDD2B, 0x43CDC09C,
            0x7B827D21, 0x7F436096, 0x7200464F, 0x76C15BF8,
            0x68860BFD, 0x6C47164A, 0x61043093, 0x65C52D24,
            0x119B4BE9, 0x155A565E, 0x18197087, 0x1CD86D30,
            0x029F3D35, 0x065E2082, 0x0B1D065B, 0x0FDC1BEC,
            0x3793A651, 0x3352BBE6, 0x3E119D3F, 0x3AD08088,
            0x2497D08D, 0x2056CD3A, 0x2D15EBE3, 0x29D4F654,
            0xC5A92679, 0xC1683BCE, 0xCC2B1D17, 0xC8EA00A0,
            0xD6AD50A5, 0xD26C4D12, 0xDF2F6BCB, 0xDBEE767C,
            0xE3A1CBC1, 0xE760D676, 0xEA23F0AF, 0xEEE2ED18,
            0xF0A5BD1D, 0xF464A0AA, 0xF9278673, 0xFDE69BC4,
            0x89B8FD09, 0x8D79E0BE, 0x803AC667, 0x84FBDBD0,
            0x9ABC8BD5, 0x9E7D9662, 0x933EB0BB, 0x97FFAD0C,
            0xAFB010B1, 0xAB710D06, 0xA6322BDF, 0xA2F33668,
            0xBCB4666D, 0xB8757BDA, 0xB5365D03, 0xB1F740B4
        ]

        url = bytes(url.lower(), 'utf-8')
        m_crc = 0xFFFFFFFF

        for c in url:
            m_crc = ((m_crc << 8) & 0xFFFFFFFF) ^ CRC_TAB[((m_crc >> 24) ^ c) & 0xFF]

        return hex(m_crc)

    def find_fanart(self, path, filename):
        filepath = join(path, filename)
        if self.is_picture(filename):
            if xbmcplugin.getSetting(int(sys.argv[1]), 'usepicasfanart') == 'true':
                return filepath
            else:
                return join(PIC_PATH, 'pic-fanart.jpg')
        elif self.is_video(filename):
            root, ext = splitext(filename)
            fanart_file = root + '-fanart' + ext
            if exists(fanart_file): # find in the same directory
                return fanart_file
            else:
                return join(PIC_PATH, 'vid-fanart.jpg')

        return None

    def find_folder_thumb(self, folderpath):
        """Check if there is a folder.[png|jpg] in the given folder.

        Args:
            folderpath (str): path to a folder

        Returns (str, None):
            path to the folder.[png|jpg] if the file exists, otherwise None
        """

        # TODO make this simple, regardless of lower/capital cases and extentions
        folder_files = ['folder.png', 'folder.jpg']
        for f in folder_files:
            folder_file = join(folderpath, f)
            if exists(folder_file):
                return folder_file
        
        return None

    def find_cached_thumb_crc(self, folderpath):
        """Get cached thumnails for the given folder
        
        This function finds thumb by computing CRC, not by openning texturexx.db.
        Thus, result is NOT 100% accurate due to the possible CRC collision.
        This method is not currently used.

        Args:
            folderpath (str): path to a folder

        Returns (str, None):
            If a cached thumbnail exists, path to the thumbnail file,
            otherwise the default thumbnail.
        """

        if not folderpath.endswith(os.path.sep):
            folderpath = folderpath + os.path.sep

        thumb_base_folder = 'special://thumbnails'
        cache_prefix = 'image://picturefolder@'
        # kodi seems(?) to add an extra '/' at the end of the folder url
        path_quoted = cache_prefix + quote(folderpath, safe='()') + '/'
        crc = self.calc_crc(path_quoted.lower())
        # For exmaple, if crc == abac56ba, 
        # the thumbnail is stored as 'special://thumbnails/a/abac56ba.[png|jpg]'
        thumb_files = (join(thumb_base_folder, crc[2], crc[2:] + '.png'),
                       join(thumb_base_folder, crc[2], crc[2:] + '.jpg'))
        for f in thumb_files:
            if xbmcvfs.exists(f):
                return f

        # Lastly, Let kodi create the thumbnail automatically.
        return None

    # TODO when?
    def find_cached_thumb_db(self, folderpath):
        """
        SELECT p.url, p.texture, t.cachedurl
        FROM path as p, texture as t
        WHERE p.url = folderpath
        AND p.texture = t.url
        """
        pass

    def add_directory(self, name, params, action, iconimage=None, fanart=None,
                      contextmenu=None, total=0, info="*", replacemenu=True, path=None):
        try:
            try:
                parameter = "&".join([param + "=" + common.quote_param(valeur) for param, valeur in params])
            except Exception as msg:
                common.log("Main.add_directory", "%s - %s" % (Exception, str(msg)), xbmc.LOGERROR)
                parameter = ""

            if path:
                # By using path instead of plugin call, kodi will generate a thumbnail with 4 pics in the folder.
                u = path
            else:
                u = sys.argv[0] + "?" + parameter + "&action=" + action + "&name=" + \
                    common.quote_param(name)

            liz = xbmcgui.ListItem(label=name)
            liz.setProperty("mypicsdb", "True")

            if iconimage:
                liz.setArt({'thumb': iconimage})
            if fanart:
                liz.setArt({'fanart': fanart})
            if contextmenu:
                liz.addContextMenuItems(contextmenu)

            return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
        except Exception as msg:
            common.log("Main.add_directory", "%s - %s" % (Exception, str(msg)), xbmc.LOGERROR)
            pass

    def add_action(self, name, params, action, iconimage, fanart=None, 
                   contextmenu=None, total=0, info="*", replacemenu=True):
        try:
            try:
                parameter = "&".join([param + "=" + common.quote_param(valeur) for param, valeur in params])
            except Exception as msg:
                common.log("Main.add_action", "%s - %s" % (Exception, str(msg)), xbmc.LOGERROR)
                parameter = ""

            u = sys.argv[0] + "?" + parameter + "&action=" + action + "&name=" + common.quote_param(name)

            liz = xbmcgui.ListItem(label=name)
            liz.setArt({'thumb': iconimage})

            if contextmenu:
                liz.addContextMenuItems(contextmenu)

            return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=False)
        except Exception as msg:
            common.log("Main.add_action", "%s - %s" % (Exception, str(msg)), xbmc.LOGERROR)
            pass

    def add_picture(self, picname, picpath, count=0, info="*", fanart=None, contextmenu=None, replacemenu=True):
        suffix = ""
        rating = ""
        coords = None
        date = None
        try:
            fullfilepath = join(picpath, picname)
            common.log("Main.add_picture", "Name = %s" % fullfilepath)

            liz = xbmcgui.ListItem(picname, info)

            try:
                # type(exiftime) == datetime.datetime, type(rating) == str
                (exiftime, rating) = MPDB.get_pic_date_rating(picpath, picname)
                date = exiftime.strftime("%Y.%m.%d") if exiftime else ""
            except Exception as msg:
               common.log("Main.add_picture", "%s - %s" % (Exception, msg), xbmc.LOGERROR)

            # is the file a video ?
            if self.is_video(picname):
                infolabels = {"date": date}
                liz.setInfo(type="video", infoLabels=infolabels)
            # or is the file a picture ?
            elif self.is_picture(picname):
                ratingmini = int(common.getaddon_setting("ratingmini"))
                if ratingmini > 0:
                    if not rating or int(rating) < ratingmini:
                        return
                coords = MPDB.get_gps(picpath, picname)
                if coords:
                    suffix = suffix + "[COLOR=C0C0C0C0][G][/COLOR]"
                _query = """
                    select coalesce(tc.TagContent,0), tt.TagType 
                    from TagTypes tt, TagContents tc, TagsInFiles tif, Files fi
                    where tt.TagType in ( 'EXIF ExifImageLength', 'EXIF ExifImageWidth' )
                    and tt.idTagType = tc.idTagType
                    and tc.idTagContent = tif.idTagContent
                    and tif.idFile = fi.idFile
                    and fi.strPath = ?
                    and fi.strFilename = ?
                """
                resolutionXY = MPDB.cur.request(_query, (picpath, picname))

                if not date:
                    infolabels = {"picturepath": picname + " " + suffix, "count": count}
                else:
                    infolabels = {"picturepath": picname + " " + suffix, "date": date, "count": count}

                try:
                    if exiftime:
                        common.log("Main.add_picture", "Picture has EXIF Date/Time %s" % exiftime)
                        infolabels["exif:exiftime"] = date
                except:
                    pass

                try:
                    if "Width" in resolutionXY[0][1]:
                        resolutionX = resolutionXY[0][0]
                        resolutionY = resolutionXY[1][0]
                    else:
                        resolutionX = resolutionXY[1][0]
                        resolutionY = resolutionXY[0][0]

                    if resolutionX != None and resolutionY != None and resolutionX != "0" and resolutionY != "0":
                        common.log("Main.add_picture",
                                   "Picture has resolution %s x %s" % (str(resolutionX), str(resolutionY)))
                        infolabels["exif:resolution"] = str(resolutionX) + ',' + str(resolutionY)
                except:
                    pass

                if int(rating) > 0:
                    common.log("Main.add_picture", "Picture has rating: %s" % rating)
                    suffix = suffix + "[COLOR=C0FFFF00]" + ("*" * int(rating)) + "[/COLOR]" + \
                        "[COLOR=C0C0C0C0]" + ("*" * (5 - int(rating))) + "[/COLOR]"

                persons = MPDB.get_pic_persons(picpath, picname)
                liz.setProperty('mypicsdb_person', persons)
                liz.setInfo(type="pictures", infoLabels=infolabels)

            liz.setProperty("mypicsdb", "True")
            liz.setLabel(picname + " " + suffix)

            if fanart:
                liz.setArt({'fanart': fanart})
                liz.setProperty('fanart_image', fanart)

            # if contextmenu:
            #    if coords:
            #        common.log("Main.add_picture", "Picture has geolocation", xbmc.LOGINFO)
            #        contextmenu.append((common.getstring(30220),\
            #                            "RunPlugin(\"%s?action='geolocate'&place='%s'&path='%s'&filename='%s'&viewmode='view'\",)" %\
            #                            (sys.argv[0],"%0.6f,%0.6f" % (coords))
            #    liz.addContextMenuItems(contextmenu)

            return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=fullfilepath, listitem=liz, isFolder=False)
        except Exception as msg:
            common.log("", "%s - %s" % (Exception, msg), xbmc.LOGERROR)

    def change_view(self):
        view_modes = {
            'skin.confluence': 500,
            'skin.aeon.nox': 551,
            'skin.confluence-vertical': 500,
            'skin.jx720': 52,
            'skin.pm3-hd': 53,
            'skin.rapier': 50,
            'skin.simplicity': 500,
            'skin.slik': 53,
            'skin.touched': 500,
            'skin.transparency': 53,
            'skin.xeebo': 55,
        }

        skin_dir = xbmc.getSkinDir()
        if skin_dir in view_modes:
            xbmc.executebuiltin('Container.SetViewMode(' + str(view_modes[skin_dir]) + ')')

    def show_home(self):
        display_all = common.getaddon_setting('m_all') == 'true'
        # last scan picture added
        if common.getaddon_setting('m_1') == 'true' or display_all:
            name = common.getstring(30209) % common.getaddon_setting("recentnbdays")
            params = [("method", "recentpicsdb"), ("period", ""), ("value", ""), 
                      ("page", "1"), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_recent_added.png")
            self.add_directory(name, params, "showpics", iconimage)

        # Last pictures
        if common.getaddon_setting('m_2') == 'true' or display_all:
            name = common.getstring(30130) % common.getaddon_setting("lastpicsnumber")
            params = [("method", "lastpicsshooted"), ("page", "1"), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_recent_shot.png")
            self.add_directory(name, params, "showpics", iconimage)

        # N random pictures
        if common.getaddon_setting('m_13') == 'true' or display_all:
            name = common.getstring(30654) % common.getaddon_setting("randompicsnumber")
            params = [("method", "random"), ("page", "1"), ("viewmode", "view"), ("onlypics", "oui")]
            iconimage = join(PIC_PATH, "folder_random.png")
            self.add_directory(name, params, "showpics", iconimage)

        # videos
        if common.getaddon_setting('m_3') == 'true' or display_all and common.getaddon_setting("usevids") == "true":
            name = common.getstring(30051)
            params = [("method", "videos"), ("page", "1"), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_videos.png")
            self.add_directory(name, params, "showpics", iconimage)

        # Saved filter wizard settings
        self.add_directory(common.getstring(30655),
                           [("wizard", "settings"), ("viewmode", "view")],
                           "showwizard",
                           join(PIC_PATH, "folder_wizard.png"))

        # show filter wizard
        self.add_action(common.getstring(30600),
                        [("wizard", "dialog"), ("viewmode", "view")], 
                        "showwizard",
                        join(PIC_PATH, "folder_wizard.png"))

        # Browse by Date
        if common.getaddon_setting('m_4') == 'true' or display_all:
            name = common.getstring(30101)
            params = [("period", "year"), ("value", ""), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_date.png")
            self.add_directory(name, params, "showdate", iconimage)

        # Browse by Folders
        if common.getaddon_setting('m_5') == 'true' or display_all:
            name = common.getstring(30102)
            params = [("method", "folders"), ("folderid", "all"), ("onlypics", "non"), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_pictures.png")
            self.add_directory(name, params, "showfolder", iconimage)

        # Browse by root folders only
        if common.getaddon_setting('m_6') == 'true' or display_all:
            name = common.getstring(30103)
            params = [("method", "folders"), ("folderid", "root"), ("onlypics", "non"), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_pictures.png")
            self.add_directory(name, params, "showfolder", iconimage)

        # Browse by child folders only
        if common.getaddon_setting('m_7') == 'true' or display_all:
            name = common.getstring(30104)
            params = [("method", "folders"), ("folderid", "child"), ("onlypics", "non"), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_pictures.png")
            self.add_directory(name, params, "showfolder", iconimage)

        # Browse by Tags
        if common.getaddon_setting('m_14') == 'true' or display_all:
            name = common.getstring(30122)
            params = [("tags", ""), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_tags.png")
            self.add_directory(name, params, "showtagtypes", iconimage)

        # Periods
        if common.getaddon_setting('m_10') == 'true' or display_all:
            name = common.getstring(30105)
            params = [("period", ""), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_date_ranges.png")
            self.add_directory(name, params, "showperiod", iconimage)

        # Collections
        if common.getaddon_setting('m_11') == 'true' or display_all:
            name = common.getstring(30150)
            params = [("collect", ""), ("method", "show"), ("viewmode", "view"),
                      ("usercollection", "")]
            iconimage = join(PIC_PATH, "folder_collections.png")
            self.add_directory(name, params, "showcollection", iconimage)

         # User Collections Only
        if common.getaddon_setting('m_11') == 'true' or display_all:
            name = common.getstring(30670)
            params = [("collect", ""), ("method", "show"), ("viewmode", "view"),
                       ("usercollection", "1")]
            iconimage = join(PIC_PATH, "folder_collections.png")
            self.add_directory(name, params, "showcollection", iconimage)


        # Global search
        if common.getaddon_setting('m_12') == 'true' or display_all:
            name = common.getstring(30098)
            params = [("searchterm", ""), ("viewmode", "view")]
            iconimage = join(PIC_PATH, "folder_search.png")
            self.add_directory(name, params, "globalsearch", iconimage)

        # picture sources
        self.add_directory(common.getstring(30099),
                           [("do", "showroots"), ("viewmode", "view")], 
                           "rootfolders",
                           join(PIC_PATH, "folder_paths.png"))

        # Settings
        self.add_action(common.getstring(30009),
                        [("showsettings", ""), ("viewmode", "view")], 
                        "showsettings",
                        join(PIC_PATH, "folder_settings.png"))

        # Translation Editor
        self.add_action(common.getstring(30620),
                        [("showtranslationeditor", ""),
                         ("viewmode", "view")], 
                         "showtranslationeditor",
                        join(PIC_PATH, "folder_translate.png"))

        # Show readme
        self.add_action(common.getstring(30123),
                        [("help", ""), ("viewmode", "view")], 
                        "help",
                        join(PIC_PATH, "folder_help.png"))

        xbmcplugin.addSortMethod(
            int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        # xbmcplugin.setPluginCategory(handle=int(sys.argv[1]), \
        # category=unquote("My Pictures Library".encode("utf-8")))
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)

    def show_date(self):
        if int(common.getaddon_setting("ratingmini")) > 0:
            min_rating = int(common.getaddon_setting("ratingmini"))
        else:
            min_rating = 0

        # period = year|month|date
        # value  = "2009"|"12/2009"|"25/12/2009"
        common.log("Main.show_date", "start")
        action = "showdate"
        monthname = common.getstring(30006).split("|")
        fullmonthname = common.getstring(30008).split("|")
        if self.args.period == "year":
            common.log("Main.show_date", "period=year")
            listperiod = MPDB.get_years(min_rating)
            nextperiod = "month"
            allperiod = ""
            action = "showdate"
            periodformat = "%Y"
            displaydate = common.getstring(30004)  # %Y
            thisdateformat = ""
            displaythisdate = ""
        elif self.args.period == "month":
            common.log("Main.show_date", "period=month")
            listperiod = MPDB.get_months(self.args.value, min_rating)
            nextperiod = "date"
            allperiod = "year"
            action = "showdate"
            periodformat = "%Y-%m"
            displaydate = common.getstring(30003)  # %b %Y
            thisdateformat = "%Y"
            displaythisdate = common.getstring(30004)  # %Y
        elif self.args.period == "date":
            common.log("Main.show_date", "period=date")
            listperiod = MPDB.get_dates(self.args.value, min_rating)
            nextperiod = "date"
            allperiod = "month"
            action = "showpics"
            periodformat = "%Y-%m-%d"
            # page=""
            displaydate = common.getstring(30002)  # "%a %d %b %Y"
            thisdateformat = "%Y-%m"
            displaythisdate = common.getstring(30003)  # "%b %Y"
        else:
            common.log("Main.show_date", "period=empty")
            listperiod = []
            nextperiod = None

        # if not None in listperiod:
        dptd = displaythisdate
        # replace %b marker by short month name
        dptd = dptd.replace("%b", monthname[strptime(self.args.value, thisdateformat).tm_mon - 1])
        # replace %B marker by long month name
        dptd = dptd.replace("%B", fullmonthname[strptime(self.args.value, thisdateformat).tm_mon - 1])
        nameperiode = strftime(dptd, strptime(self.args.value, thisdateformat))

        common.log("", "dptd = " + dptd)
        common.log("", "nameperiode = " + nameperiode)
        common.log("", "allperiod = " + allperiod)

        count = MPDB.count_pics_in_period(
            allperiod, self.args.value, min_rating)
        if count > 0:
            self.add_directory(name=common.getstring(30100) % (nameperiode, count),
                               params=[("method", "date"), ("period", allperiod), ("value", self.args.value),
                                       ("page", ""), ("viewmode", "view")],
                               action="showpics",
                               iconimage=join(PIC_PATH, "folder_date.png"),
                               contextmenu=[(common.getstring(30152),
                                             "RunPlugin(\"%s?" % (sys.argv[0]) +
                                             "action=addfolder&method=date&period=%s&value=%s&viewmode=scan\")" % \
                                              (allperiod, self.args.value)), ]
                               )
        count = MPDB.count_pics_wo_imagedatetime(
            allperiod, self.args.value, min_rating)
        if count > 0 and self.args.period == "year":
            self.add_directory(name=common.getstring(30054) % (count),
                               params=[("method", "date"), ("period", "wo"), ("value", self.args.value), 
                                       ("page", ""), ("viewmode", "view")],
                               # paramètres
                               action="showpics",  # action
                               iconimage=join(
                                   PIC_PATH, "folder_date.png"),  # icone
                               contextmenu=[(common.getstring(30152),
                                             "RunPlugin(\"%s?" % ( sys.argv[0]) +
                                             "action=addfolder&method=date&period=%s&value=%s&viewmode=scan\")" % \
                                             (allperiod, self.args.value)), ])

        total = len(listperiod)
        for period in listperiod:
            if period:
                if action == "showpics":
                    context = [(common.getstring(30152),
                                "RunPlugin(\"%s?" % (sys.argv[0]) +
                                "action=addfolder&method=date&period=%s&value=%s&viewmode=scan\")" % \
                                (nextperiod, period)), ]
                else:
                    context = [(common.getstring(30152),
                                "RunPlugin(\"%s?" % (sys.argv[0]) +
                                "action=addfolder&method=date&period=%s&value=%s&viewmode=scan\")" % \
                                (self.args.period, period)), ]

                try:
                    dateformat = strptime(period, periodformat)
                    self.add_directory(
                        name="%s (%s %s)" % (strftime(self.prettydate(displaydate, dateformat), dateformat),
                                             MPDB.count_pics_in_period(
                                                 self.args.period, period, min_rating),
                                             common.getstring(30050)),  # libellé
                        params=[("method", "date"), ("period", nextperiod),
                                ("value", period), ("viewmode", "view")], # paramètres
                        action=action,  # action
                        iconimage=join(PIC_PATH, "folder_date.png"),  # icone
                        contextmenu=context,  # menucontextuel
                        total=total)  # nb total d'éléments
                except:
                    pass

        xbmcplugin.addSortMethod(
            int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_folders(self):
        common.log("Main.show_folders", "start")
        
        if int(common.getaddon_setting("ratingmini")) > 0:
            min_rating = int(common.getaddon_setting("ratingmini"))
        else:
            min_rating = 0
        
        if self.args.folderid == 'all':  # get all folders
            childrenfolders = [row for row in MPDB.cur.request(
                "SELECT idFolder,FolderName FROM Folders")]
        elif self.args.folderid == 'root':  # get root folders
            childrenfolders = [row for row in MPDB.cur.request(
                "SELECT idFolder,FolderName FROM Folders WHERE ParentFolder is null")]
        elif self.args.folderid == 'child':  # get child folders
            childrenfolders = [row for row in MPDB.cur.request(
                "SELECT idFolder,FolderName FROM Folders WHERE ParentFolder is NOT null")]
        else:  # else, get subfolders for given folder Id
            childrenfolders = [row for row in MPDB.cur.request_with_binds(
                "SELECT idFolder,FolderName FROM Folders WHERE ParentFolder=?", (self.args.folderid,))]

        # show folders in the folder
        for idchildren, childrenfolder in childrenfolders:
            common.log("Main.show_folders", "children folder = %s" % childrenfolder)
            path = MPDB.cur.request_with_binds(
                "SELECT FullPath FROM Folders WHERE idFolder = ?", (idchildren,))[0][0]
            count = MPDB.count_pics_in_folder(idchildren, min_rating)
            if count > 0:
                name="%s (%s %s)" % (childrenfolder, count, common.getstring(30050))
                params=[("method", "folders"), ("folderid", str(idchildren)), 
                        ("onlypics", "non"), ("viewmode", "view")]
                contextmenu=[(common.getstring(30212), # Exclude this folder from database
                            "Container.Update(\"%s?" % (sys.argv[0]) +
                            "action=rootfolders&do=addrootfolder&addpath=%s&exclude=1&viewmode=view\",)" % \
                            (common.quote_param(path))),
                            (common.getstring(30152), # Add to collection
                             "RunPlugin(\"%s?" % (sys.argv[0]) +
                             "action=addfolder&method=folders&viewmode=scan&folderid=%s\")" % \
                             (common.quote_param(str(idchildren))))]

                thumb = self.find_folder_thumb(path) or None
                self.add_directory(name=name, 
                                   params=params,
                                   action="showfolder",
                                   iconimage=thumb,
                                   contextmenu=contextmenu,
                                   total=len(childrenfolders),
                                   path=path)

        # maintenant, on liste les photos si il y en a, du dossier en cours
        if min_rating > 0:
            _query = """
                    SELECT p.FullPath, f.strFilename 
                    FROM Files f, Folders p 
                    WHERE f.idFolder=p.idFolder AND f.idFolder=? AND f.ImageRating > ? 
                    Order by f.imagedatetime
            """
            picsfromfolder = [row for row in MPDB.cur.request_with_binds(
                _query, (self.args.folderid, min_rating,))]
        else:
            _query = """
                SELECT p.FullPath, f.strFilename 
                FROM Files f, Folders p 
                WHERE f.idFolder=p.idFolder AND f.idFolder=? 
                Order by f.imagedatetime
            """
            picsfromfolder = [row for row in MPDB.cur.request_with_binds(
                _query, (self.args.folderid,))]

        # show pictures in the folder
        count = 0

        # context.append((common.getstring(30303),"SlideShow(%s%s,recursive,notrandom)"%(sys.argv[0],sys.argv[2])))
        for path, filename in picsfromfolder:
            common.log("Main.show_folders", "pic's path = %s  pic's name = %s" % (path, filename))
            count = count + 1
            context = [(common.getstring(30152), # Add to collection
                    "RunPlugin(\"%s?" % (sys.argv[0]) +
                    "action=addtocollection&viewmode=view&path=%s&filename=%s\")" % \
                    (common.quote_param(path), common.quote_param(filename)))]            
            self.add_picture(filename, path, count=count, contextmenu=context,
                             fanart=self.find_fanart(path, filename))

        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_PROGRAM_COUNT)

        self.change_view()

        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_translationeditor(self):
        ui = translationeditor.TranslationEditor("script-mypicsdb-translationeditor.xml", 
                                                 common.getaddon_path(), "Default")
        ui.doModal()
        del ui

    def show_map(self):
        """get a google map for the given place 
        
        place is a string for an address, or a couple of gps lat/lon data
        """
        
        common.log("Main.show_map", "Start")
        try:
            path = self.args.path
            filename = self.args.filename
            joined = join(path, filename)
        except:
            common.log("Main.show_map", "Error with parameter", xbmc.LOGERROR)
            return

        common.log("Main.show_map", "Open Dialog", xbmc.LOGINFO)
        ui = googlemaps.GoogleMap(
            "script-mypicsdb-googlemaps.xml", common.getaddon_path(), "Default")
        ui.set_file(joined)
        ui.set_place(self.args.place)
        ui.set_datapath(DATA_PATH)
        ui.doModal()
        del ui
        common.log("Main.show_map", "Close Dialog", xbmc.LOGINFO)

    def show_help(self):
        viewer.Viewer()

    def show_settings(self):
        xbmcaddon.Addon().openSettings()

    def show_wizard(self):
        if self.args.wizard == 'dialog':
            global GlobalFilterTrue, GlobalFilterFalse, GlobalMatchAll, g_start_date, g_end_date

            common.log("Main.show_wizard", "Show Dialog")
            ui = filterwizard.FilterWizard(
                "script-mypicsdb-filterwizard.xml", common.getaddon_path(), "Default")
            ui.set_delegate(filterwizard_delegate)
            ui.doModal()
            del ui
            common.log("Main.show_wizard", "Delete Dialog")

            newtagtrue = ""
            newtagfalse = ""
            matchall = GlobalMatchAll
            start_date = g_start_date
            end_date = g_end_date
            if len(GlobalFilterTrue) > 0:
                for tag in GlobalFilterTrue:
                    if len(newtagtrue) == 0:
                        newtagtrue = tag
                    else:
                        newtagtrue += "|||" + tag
                common.log("Main.show_wizard", newtagtrue)

            if len(GlobalFilterFalse) > 0:
                for tag in GlobalFilterFalse:
                    if len(newtagfalse) == 0:
                        newtagfalse = tag
                    else:
                        newtagfalse += "|||" + tag

            if len(GlobalFilterTrue) > 0 or len(GlobalFilterFalse) > 0 or start_date != '' or end_date != '':
                xbmc.executebuiltin("Container.Update(%s?" % (sys.argv[0]) +
                    "action=showpics&viewmode=view&method=wizard&matchall=%s&kw=%s&nkw=%s&start=%s&end=%s)" %\
                        (matchall, common.quote_param(newtagtrue), common.quote_param(newtagfalse),
                         start_date, end_date))
        elif self.args.wizard == 'settings':
            filterlist = MPDB.filterwizard_list_filters()
            total = len(filterlist)
            for filtername in filterlist:
                common.log('Main.show_wizard', filtername)
                params=[("method", "wizard_settings"), ("viewmode", "view"), ("filtername", filtername), 
                        ("period", ""), ("value", ""), ("page", "1")]
                self.add_directory(name="%s" % (filtername),
                                   params=params,
                                   action="showpics",
                                   iconimage=join(PIC_PATH, "folder_wizard.png"),
                                   contextmenu=[(common.getstring(30152),
                                                 "RunPlugin(\"%s?" % (sys.argv[0]) +
                                                 "action=addfolder&method=wizard_settings&filtername=%s&viewmode=scan\")" %\
                                                     (filtername)), ],
                                   total=total)
            xbmcplugin.addSortMethod(
                int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
            xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_tagtypes(self):
        if int(common.getaddon_setting("ratingmini")) > 0:
            min_rating = int(common.getaddon_setting("ratingmini"))
        else:
            min_rating = 0

        listtags = MPDB.list_tagtypes_count(min_rating)
        total = len(listtags)
        common.log("Main.show_tagtypes", "total # of tag types = %s" % total)
        for tag, nb in listtags:
            if nb:
                self.add_directory(name="%s (%s %s)" % (tag, nb, common.getstring(30052)),  # libellé
                                   params=[("method", "tagtype"), ("tagtype", tag), ("page", "1"),
                                           ("viewmode", "view")], # paramètres
                                   action="showtags",  # action
                                   iconimage=join(PIC_PATH, "folder_tags.png"),  # icone
                                   # contextmenu   = [('','')],
                                   total=total)  # nb total d'éléments
        xbmcplugin.addSortMethod(
            int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_tags(self):
        if int(common.getaddon_setting("ratingmini")) > 0:
            min_rating = int(common.getaddon_setting("ratingmini"))
        else:
            min_rating = 0

        tagtype = self.args.tagtype
        listtags = [k for k in MPDB.list_tags_count(tagtype, min_rating)]
        total = len(listtags)
        common.log("Main.show_tags", "total # of tags = %s" % total)
        for tag, nb in listtags:
            if nb:
                contextmenu=[(common.getstring(30152),
                             "RunPlugin(\"%s?" % (sys.argv[0]) +
                             "action=addfolder&method=tag&tag=%s&tagtype=%s&viewmode=scan\")" % \
                                 (common.quote_param(tag), tagtype)),
                             (common.getstring(30061),
                              "RunPlugin(\"%s?" % (sys.argv[0]) +
                              "action=showpics&method=tag&viewmode=zip&name=%s&tag=%s&tagtype=%s\")" % \
                                  (common.quote_param(tag), common.quote_param(tag), tagtype)),
                             (common.getstring(30062),
                              "RunPlugin(\"%s?" % (sys.argv[0]) +
                                  "action=showpics&method=tag&viewmode=export&name=%s&tag=%s&tagtype=%s\")" % \
                                      (common.quote_param(tag), common.quote_param(tag), tagtype))]
                self.add_directory(name="%s (%s %s)" % (tag, nb, common.getstring(30050)),  # libellé
                                   params=[("method", "tag"), ("tag", tag), ("tagtype", tagtype), ("page", "1"),
                                           ("viewmode", "view")],
                                   # paramètres
                                   action="showpics",  # action
                                   iconimage=join(PIC_PATH, "folder_tags.png"),  # icone
                                   contextmenu=contextmenu,  # menucontextuel
                                   total=total)  # nb total d'éléments
        xbmcplugin.addSortMethod(
            int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def show_period(self):  # TODO finished the datestart and dateend editing
        common.log("show_period", "started")
        update = False
        self.add_directory(name=common.getstring(30106),
                           params=[("period", "setperiod"),
                                   ("viewmode", "view")],  # paramètres
                           action="showperiod",  # action
                           iconimage=join(
                               PIC_PATH, "folder_date_ranges.png"),  # icone
                           contextmenu=None)  # menucontextuel
        # If We previously choose to add a new period, this test will ask user for setting the period :
        if self.args.period == "setperiod":
            common.log("show_period", "setperiod")
            # the choice of the date is made with pictures in database (datetime of pics are used)
            dateofpics = MPDB.get_pics_dates()
            nameddates = [strftime(self.prettydate(common.getstring(30002), strptime(date, "%Y-%m-%d")),
                                   strptime(date, "%Y-%m-%d")) for date in dateofpics]
            common.log("show_period >> namedates", nameddates)

            if len(nameddates):
                dialog = xbmcgui.Dialog()
                # dateofpics) choose the start date
                rets = dialog.select(common.getstring(30107), 
                                     ["[[%s]]" % common.getstring(30114)] + nameddates)
                if not rets == -1:  # is not canceled
                    if rets == 0:  # input manually the date
                        d = dialog.numeric(1, common.getstring(30117),
                                           strftime("%d/%m/%Y", strptime(dateofpics[0], "%Y-%m-%d")))
                        common.log("period", str(d))
                        if d != '':
                            datestart = strftime("%Y-%m-%d", strptime(d.replace(" ", "0"), "%d/%m/%Y"))
                        else:
                            datestart = ''
                        deb = 0
                    else:
                        datestart = dateofpics[rets - 1]
                        deb = rets - 1

                    if datestart != '':
                        # dateofpics[deb:])#choose the end date (all dates before startdate are ignored to preserve begin/end)
                        retf = dialog.select(common.getstring(30108), ["[[%s]]" % common.getstring(30114)] + nameddates[deb:])  
                        if not retf == -1:  # if end date is not canceled...
                            if retf == 0:  # choix d'un date de fin manuelle ou choix précédent de la date de début manuelle
                                d = dialog.numeric(1, common.getstring(30118),
                                                   strftime("%d/%m/%Y", strptime(dateofpics[-1], "%Y-%m-%d")))
                                if d != '':
                                    dateend = strftime(
                                        "%Y-%m-%d", strptime(d.replace(" ", "0"), "%d/%m/%Y"))
                                else:
                                    dateend = ''
                                deb = 0
                            else:
                                dateend = dateofpics[deb + retf - 1]

                            if dateend != '':
                                # now input the title for the period
                                #
                                kb = xbmc.Keyboard(common.getstring(30109) % (datestart, dateend),
                                                   common.getstring(30110), False)
                                kb.doModal()
                                if (kb.isConfirmed()):
                                    titreperiode = kb.getText()
                                else:
                                    titreperiode = common.getstring(
                                        30109) % (datestart, dateend)
                                # add the new period inside the database
                                MPDB.period_add(titreperiode, datestart, dateend)
                update = True
            else:
                common.log("show_period", "No pictures with an EXIF date stored in DB")

        # search for inbase periods and show periods
        for periodname, dbdatestart, dbdateend in MPDB.periods_list():
            datestart, dateend = MPDB.period_dates_get_pics(dbdatestart, dbdateend)
            period = common.getstring(30113) % (datestart.strftime(common.getstring(30002)), 
                                                dateend.strftime(common.getstring(30002)))
            contextmenu=[(common.getstring(30111),
                          "RunPlugin(\"%s?" % (sys.argv[0]) +
                          "action=removeperiod&viewmode=view&periodname=%s&period=period\")" % \
                              (common.quote_param(periodname))),
                         (common.getstring(30112),
                          "RunPlugin(\"%s?" % (sys.argv[0]) +
                          "action=renameperiod&viewmode=view&periodname=%s&period=period\")" % \
                              (common.quote_param(periodname))),
                         (common.getstring(30152),
                          "RunPlugin(\"%s?" % (sys.argv[0]) +
                          "action=addfolder&method=date&period=period&datestart=%s&dateend=%s&viewmode=scan\")" % \
                              (datestart, dateend))]
                                            
            self.add_directory(name="%s [COLOR=C0C0C0C0](%s)[/COLOR]" % (periodname, period), # libellé
                               params=[("method", "date"), ("period", "period"), ("datestart", datestart),
                                       ("dateend", dateend), ("page", "1"), ("viewmode", "view")], # paramètres
                               action="showpics", # action
                               iconimage=join(PIC_PATH, "folder_date_ranges.png"), # icone
                               contextmenu=contextmenu) # menucontextuel

        xbmcplugin.addSortMethod(
            int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)

        self.change_view()

        xbmcplugin.endOfDirectory(int(sys.argv[1]), updateListing=update)

    def show_collection(self):
        if int(common.getaddon_setting("ratingmini")) > 0:
            min_rating = int(common.getaddon_setting("ratingmini"))
        else:
            min_rating = 0

        # herve502
        from xml.dom.minidom import parseString
        # /herve502
        common.log("show_collection", "started")
        if self.args.method == "setcollection":  # ajout d'une collection
            kb = xbmc.Keyboard("", common.getstring(30155), False)
            kb.doModal()
            if (kb.isConfirmed()):
                namecollection = kb.getText()
            else:
                # name input for collection has been canceled
                return
            # create the collection in the database
            common.log("show_collection", "setcollection = %s" %
                       namecollection)
            MPDB.collection_new(namecollection)
            refresh = True
        # import a collection from Filter Wizard Settings
        elif self.args.method == "importcollection_wizard":  
            filters = MPDB.filterwizard_list_filters()
            dialog = xbmcgui.Dialog()
            ret = dialog.select(common.getstring(30608), filters)
            if ret > -1:
                # ask user for name of new collection
                collection_name = filters[ret]
                kb = xbmc.Keyboard(
                    collection_name, common.getstring(30155), False)
                kb.doModal()
                if (kb.isConfirmed()):
                    collection_name = kb.getText()
                    # MPDB.collection_add_dyn_data(collection_name, filters[ret], 'FilterWizard')
                    rows = MPDB.filterwizard_get_pics_from_filter(filters[ret], 0)

                    if rows != None:
                        MPDB.collection_new(collection_name)
                        for pathname, filename in rows:
                            MPDB.collection_add_pic(
                                collection_name, pathname, filename)
                    else:
                        common.log("show_collection", str(filters[ret]) + 
                                   " is empty and therefore not created.",
                                   xbmc.LOGINFO)
            refresh = True

        # herve502
        elif self.args.method == "importcollection_picasa":  # import xml from picasa
            dialog = xbmcgui.Dialog()
            importfile = dialog.browse(1, common.getstring(30162), "files", ".xml", True, False, "")
            if not importfile:
                return

            not_imported = ""
            try:
                fh = open(importfile, 'r')
                importfile = fh.read()
                fh.close()

                album = parseString(importfile)

                collection_name = album.getElementsByTagName(
                    "albumName")[0].firstChild.data.encode("utf-8").strip()

                # ask user if title as new collection name is correct
                kb = xbmc.Keyboard(
                    collection_name, common.getstring(30155), False)
                kb.doModal()
                if (kb.isConfirmed()):
                    collection_name = kb.getText()

                    # create the collection in the database
                    common.log("show_collection",
                               "setcollection = %s" % collection_name)

                    MPDB.collection_new(collection_name)
                    
                    # Xycl get pictures with complete path name
                    file_names = album.getElementsByTagName("itemOriginalPath")
                    for itemName in file_names:  # iterate over the nodes
                        filepath = itemName.firstChild.data.encode(
                            "utf-8").strip()  # get data ("name of picture")
                        filename = basename(filepath)
                        pathname = dirname(filepath)
                        try:
                            # Path in DB can end with "/" or "\" or without the path delimiter.
                            # Therefore it's a little bit tricky to test for exsistence of path.

                            # At first we use what is stored in DB

                            # if no row returns then the [0] at the end of select below will raise an exception.
                            # easy test of existence of file in DB
                            _query = """
                                select strFilename, strPath 
                                from Files 
                                where lower(strFilename) = ? and lower(strPath) = ?"
                            """
                            filename, pathname = MPDB.cur.request_with_binds(
                                _query, (filename.lower(), pathname.lower()))[0]
                            MPDB.collection_add_pic(collection_name, pathname, filename)
                        except:
                            try:
                                # Secondly we use the stored path in DB without last character
                                _query = """
                                    select strFilename, strPath 
                                    from Files 
                                    where lower(strFilename) = ? and substr(lower(strPath), 1, length(strPath)-1) = ?"
                                """
                                filename, pathname = MPDB.cur.request_with_binds(
                                    _query, (filename.lower(), pathname.lower()))[0]
                                MPDB.collection_add_pic(collection_name, pathname, filename)
                            except:
                                not_imported += common.getstring(30166) % (filename, pathname)
                                pass

            except:
                dialog.ok(common.getstring(30000), common.getstring(30163))
                return

            if not_imported != "":
                not_imported = common.getstring(30165) + not_imported
                viewer.Viewer(header=common.getstring(30167), text=not_imported)
            refresh = True
        # /herve502
        else:
            refresh = False
        if not self.args.usercollection:
            self.add_directory(name=common.getstring(30160), # Create a new collection
                            params=[("method", "setcollection"), ("collect", ""),
                            ("viewmode", "view"), ],  # paramètres
                            action="showcollection",  # action
                            iconimage=join(PIC_PATH, "folder_collections.png"),  # icone
                            contextmenu=None)  # menucontextuel
            self.add_directory(name=common.getstring(30168), # Import album from saved filter setting
                            params=[("method", "importcollection_wizard"),
                                    ("collect", ""), ("viewmode", "view"), ],
                            # paramètres
                            action="showcollection",  # action
                            iconimage=join(PIC_PATH, "folder_collections.png"),  # icone
                            contextmenu=None)  # menucontextuel
            # herve502
            self.add_directory(name=common.getstring(30162), # Import album from Picasa xml
                            params=[("method", "importcollection_picasa"),
                                    ("collect", ""), ("viewmode", "view"), ], # paramètres
                            action="showcollection",  # action
                            iconimage=join(PIC_PATH, "folder_collections.png"),  # icone
                            contextmenu=None)  # menucontextuel
            # /herve520
        for collection in MPDB.collections_list():
            contextmenu = [(common.getstring(30303), # Show the slideshow
                            "RunPlugin(\"%s?" % (sys.argv[0]) +
                            "action=showpics&method=collection&viewmode=slideshow&page=1&collect=%s\")" % \
                                (common.quote_param(collection[0]))),
                           (common.getstring(30149), # Add playlist to collection
                            "RunPlugin(\"%s?" % (sys.argv[0]) +
                            "action=collectionaddplaylist&viewmode=view&collect=%s\")" % \
                                (common.quote_param(collection[0]))),
                           (common.getstring(30158), # Remove this collection
                            "RunPlugin(\"%s?" % (sys.argv[0]) +
                            "action=removecollection&viewmode=view&collect=%s\")" % \
                                (common.quote_param(collection[0]))),
                           (common.getstring(30159), # Rename this collection
                            "RunPlugin(\"%s?" % (sys.argv[0]) +
                            "action=renamecollection&viewmode=view&collect=%s\")" % \
                                (common.quote_param(collection[0]))),
                           (common.getstring(30061), # Archive those pictures
                            "RunPlugin(\"%s?" % (sys.argv[0]) +
                            "action=showpics&method=collection&viewmode=zip&name=%s&collect=%s\")" % \
                                (common.quote_param(collection[0]), common.quote_param(collection[0]))),
                           (common.getstring(30062), # Export those pictures to...
                            "RunPlugin(\"%s?" % (sys.argv[0]) +
                            "action=showpics&method=collection&viewmode=export&name=%s&collect=%s\")" % \
                                (common.quote_param(collection[0]), common.quote_param(collection[0])))]
            self.add_directory(name=collection[0], # Show pictures
                               params=[("method", "collection"), ("viewmode", "view"),
                                       ("collect", (common.quote_param(collection[0])))],
                               action="showpics",
                               iconimage=join(PIC_PATH, "folder_collections.png"),
                               contextmenu=contextmenu)

        xbmcplugin.addSortMethod(
            int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)

        self.change_view()

        xbmcplugin.endOfDirectory(int(sys.argv[1]), updateListing=refresh)

    def global_search(self):
        if int(common.getaddon_setting("ratingmini")) > 0:
            min_rating = int(common.getaddon_setting("ratingmini"))
        else:
            min_rating = 0

        if not self.args.searchterm:
            refresh = 0
            filters = MPDB.search_list_saved()
            dialog = xbmcgui.Dialog()

            ret = dialog.select(common.getstring(30121), filters)
            if ret > 0:
                motrecherche = filters[ret]
                # Save is important because there are only 10 saved searches and 
                # due to save call the search gets a new key!!!
                MPDB.search_save(motrecherche)
            elif ret == -1:
                common.log("Main.global_search", "user cancelled search")
                xbmcplugin.endOfDirectory(
                    int(sys.argv[1]), updateListing=refresh)
                return

            else:
                kb = xbmc.Keyboard("", common.getstring(30115), False)
                kb.doModal()
                if (kb.isConfirmed()):
                    motrecherche = kb.getText()
                    if motrecherche == '':
                        xbmcplugin.endOfDirectory(
                            int(sys.argv[1]), updateListing=refresh)
                        return

                    MPDB.search_save(motrecherche)
                    common.log("Main.global_search",
                               "user entered %s" % motrecherche)
                else:
                    common.log("Main.global_search", "user cancelled search")
                    xbmcplugin.endOfDirectory(
                        int(sys.argv[1]), updateListing=refresh)
                    return

        else:
            motrecherche = self.args.searchterm
            common.log("Main.global_search", "search %s" % motrecherche)
            refresh = 1

        listtags = [k for k in MPDB.list_tagtypes_count(min_rating)]

        result = False
        for tag, _ in listtags:
            common.log("Main.global_search", "Search %s in %s" %
                       (motrecherche, tag))
            compte = MPDB.search_in_files(
                tag, motrecherche, min_rating, count=True)
            if compte:
                result = True
                contextmenu = [(common.getstring(30152),
                                "RunPlugin(\"%s?" % (sys.argv[0]) +
                                "action=addfolder&method=search&field=%s&searchterm=%s&viewmode=scan\")" % \
                                    (tag, motrecherche))]
                self.add_directory(name=common.getstring(30116) % (compte, motrecherche, tag),
                                   # files_fields_description.has_key(colname) 
                                   # and files_fields_description[colname] or colname),
                                   params=[("method", "search"), ("field", "%s" % tag),
                                           ("searchterm", "%s" % motrecherche), ("page", "1"),
                                           ("viewmode", "view")],
                                   # paramètres
                                   action="showpics",  # action
                                   iconimage=join(PIC_PATH, "folder_search.png"),
                                   contextmenu=contextmenu)  # menucontextuel
        if not result:
            dialog = xbmcgui.Dialog()
            dialog.ok(common.getstring(30000),
                      common.getstring(30119) % motrecherche)
            refresh = 0
            xbmcplugin.endOfDirectory(int(sys.argv[1]), updateListing=refresh)
            return
        xbmcplugin.addSortMethod(
            int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)

        self.change_view()

        xbmcplugin.endOfDirectory(int(sys.argv[1]), updateListing=refresh)

    def get_picture_sources(self):
        jsonResult = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Files.GetSources", "params": {"media": "pictures"}, "id": 1}')
        shares = eval(jsonResult)
        shares = shares['result']
        shares = shares.get('sources')

        if (shares == None):
            shares = []

        names = []
        sources = []
        for s in shares:

            if s['file'].startswith('addons://'):
                pass
            else:
                sources.append(s['file'])
                names.append(s['label'])
        return names, sources

    def show_roots(self):
        # show the root folders
        if self.args.do == "addroot" or self.args.do == "addpicturessource":  # add a root to scan
            if self.args.do == "addroot":
                dialog = xbmcgui.Dialog()
                newroot = dialog.browse(0, common.getstring(30201), 'pictures')

                if not newroot:
                    return
            elif self.args.do == "addpicturessource":
                _names, sources = self.get_picture_sources()

                for source in sources:
                    try:
                        if source.startswith('multipath://'):
                            common.log(
                                "Main.show_roots", 'Adding Multipath: "%s"' % unquote(source))
                            newpartialroot = source[12:-1].split('/')
                            for item in newpartialroot:
                                # TODO : traiter le exclude (=0 pour le moment) pour gérer les chemins à exclure
                                MPDB.add_root_folder(unquote(item), True, True, 0)  
                                common.log("Main.show_roots", 
                                           'Multipath addroot for part "%s" done' % unquote(item))
                        else:
                            # TODO : traiter le exclude (=0 pour le moment) pour gérer les chemins à exclure
                            MPDB.add_root_folder(source, True, True, 0)  
                            common.log("Main.show_roots",
                                       'Singlepath addroot "%s" done' % source)

                        xbmc.executebuiltin("Container.Refresh(\"%s?" % (sys.argv[0]) +
                            "action=rootfolders&do=showroots&exclude=0&viewmode=view\")")

                    except:
                        common.log("Main.show_roots", 
                                   'MPDB.add_root_folder failed for "%s"' % source, xbmc.LOGERROR)

                if common.getaddon_setting('scanning') == 'false':
                    common.run_script("%s, --refresh" % "script.module.mypicsdb2scan")
                    return
            else:
                return

            if str(self.args.exclude) == "1":
                MPDB.add_root_folder(newroot, 0, 0, 1)
                xbmc.executebuiltin("Container.Refresh(\"%s?" % (sys.argv[0]) +
                    "action=rootfolders&do=showroots&exclude=1&viewmode=view\")")
                common.log("Main.show_roots",
                           'Exclude folder "%s" added' % newroot)
                # xbmc.executebuiltin("Notification(%s,%s,%s,%s)" 
                # % (common.getstring(30000),common.getstring(30204),3000,join(home,"icon.png")))
                dialogok = xbmcgui.Dialog()
                dialogok.ok(common.getstring(30000), 
                            common.getstring(30217) + ' ' + common.getstring(30218))
            else:
                recursive = dialog.yesno(common.getstring(30000),
                                         common.getstring(30202)) and 1 or 0  # browse recursively this folder ?
                # dialog.yesno(common.getstring(30000),common.getstring(30203)) and 1 or 0 
                # Remove files from database if pictures does not exists?
                update = True

                try:
                    if newroot.startswith('multipath://'):
                        common.log("Main.show_roots",
                                   'Adding Multipath: "%s"' % unquote(newroot))
                        newpartialroot = newroot[12:-1].split('/')
                        # TODO : traiter le exclude (=0 pour le moment) pour gérer les chemins à exclure
                        for item in newpartialroot:
                            MPDB.add_root_folder(unquote(item), recursive, update, 0)  
                            common.log("Main.show_roots", 
                                       'Multipath addroot for part "%s" done' % unquote(item))
                    else:
                        # TODO : traiter le exclude (=0 pour le moment) pour gérer les chemins à exclure
                        MPDB.add_root_folder(newroot, recursive, update, 0)  
                        common.log("Main.show_roots",
                                   'Singlepath addroot "%s" done' % newroot)

                    xbmc.executebuiltin("Container.Refresh(\"%s?" % (sys.argv[0]) +
                                        "action=rootfolders&do=showroots&exclude=0&viewmode=view\")")

                except:
                    common.log("Main.show_roots", 
                               'MPDB.add_root_folder failed for "%s"' % newroot, xbmc.LOGERROR)
                common.show_notification(common.getstring(30000), 
                                         common.getstring(30204), 3000, join(home, "icon.png"))

                if common.getaddon_setting('scanning') == 'false':
                    # do a scan now ?
                    if dialog.yesno(common.getstring(30000), common.getstring(30206)):
                        if newroot.startswith('multipath://'):
                            common.log("Main.show_roots", "Multipaths")
                            newpartialroot = newroot[12:-1].split('/')
                            for item in newpartialroot:
                                common.log(
                                    "Main.show_roots", 'Starting scanpath "%s"' % unquote(item))
                                common.run_script("%s,%s --rootpath=%s" % (
                                    "script.module.mypicsdb2scan", recursive and "-r, " or "",
                                    common.quote_param(unquote(item))))

                                common.log(
                                    "Main.show_roots", 'Scanpath "%s" started' % unquote(item))
                        else:
                            common.log("Main.show_roots",
                                       'Starting scanpath "%s"' % newroot)
                            common.run_script("%s,%s --rootpath=%s" % (
                                "script.module.mypicsdb2scan", recursive and "-r, " or "", common.quote_param(newroot)))
                            common.log("Main.show_roots",
                                       'Scanpath "%s" started' % newroot)
                else:
                    return
                return

        # I don't think that this is ever called because no user knows about it
        elif self.args.do == "addrootfolder":
            if str(self.args.exclude) == "1":
                common.log("Main.show_roots", 
                           'addrootfolder "%s" (exclude) from context menu' % self.args.addpath)
                MPDB.add_root_folder(self.args.addpath, 0, 0, 1)

        elif self.args.do == "delroot":
            try:
                dialog = xbmcgui.Dialog()
                if dialog.yesno(common.getstring(30250), common.getstring(30251) % self.args.delpath):
                    common.log("Main.show_roots", 'delroot "%s"' % self.args.delpath)
                    MPDB.delete_root(self.args.delpath)
                    if self.args.delpath != 'neverexistingpath':
                        common.show_notification(common.getstring(30000), 
                                                 common.getstring(30205), 
                                                 3000, 
                                                 join(home, "icon.png"))
            except IndexError as msg:
                common.log("Main.show_roots", 'delroot IndexError %s - %s' %
                           (IndexError, msg), xbmc.LOGERROR)

        elif self.args.do == "rootclic":
            if common.getaddon_setting('scanning') == 'false':
                if str(self.args.exclude) == "0":
                    path, recursive, update, exclude = MPDB.get_root_folders(
                        self.args.rootpath)
                    common.run_script("%s,%s --rootpath=%s" % (
                        "script.module.mypicsdb2scan", recursive and "-r, " or "", common.quote_param(path)))
                else:
                    pass
            else:
                # dialogaddonscan était en cours d'utilisation, on return
                return
        elif self.args.do == "scanall":
            if common.getaddon_setting('scanning') == 'false':
                common.run_script("script.module.mypicsdb2scan,--database")
                return
            else:
                # dialogaddonscan était en cours d'utilisation, on return
                return
        elif self.args.do == "refreshpaths":
            if common.getaddon_setting('scanning') == 'false':
                common.run_script("script.module.mypicsdb2scan,--refresh")
                return

        if int(sys.argv[1]) >= 0:
            excludefolders = []
            includefolders = []
            for path, recursive, update, exclude in MPDB.get_all_root_folders():
                if exclude:
                    excludefolders.append([path, recursive, update])
                else:
                    includefolders.append([path, recursive, update])

            # Add XBMC picutre sources to database
            self.add_action(name=common.getstring(30216), # Add all Kodi pictures sources to database                            # paramètres
                            params=[("do", "addpicturessource"),
                                    ("viewmode", "view"), ("exclude", "0")],
                            action="rootfolders",  # action
                            iconimage=join(PIC_PATH, "folder_paths.png"), # icone
                            contextmenu=None)  # menucontextuel

            # Add a path to database
            self.add_action(name=common.getstring(30208), # Add a path to database
                            params=[("do", "addroot"), ("viewmode", "view"),
                                    ("exclude", "0")], # paramètres
                            action="rootfolders", # action
                            iconimage=join(PIC_PATH, "folder_paths.png"), # icone
                            contextmenu=None) # menucontextuel

            # Scan all paths
            if len(includefolders) > 0:
                self.add_action(name=common.getstring(30213),  # Search for new & changed pictures
                                params=[("do", "scanall"), ("viewmode", "view"),], # paramètres
                                action="rootfolders",  # action
                                iconimage=join(PIC_PATH, "folder_paths.png"), # icone
                                contextmenu=None)  # menucontextuel

            # Add new pictures
            if len(includefolders) > 0:
                self.add_action(name=common.getstring(30249), # Search for new pictures
                                params=[("do", "refreshpaths"), ("viewmode", "view"),],  # paramètres
                                action="rootfolders", # action
                                iconimage=join(PIC_PATH, "folder_paths.png"), # icone
                                contextmenu=None)  # menucontextuel

            # Show included folders
            for path, recursive, update in includefolders:
                srec = recursive == 1 and "ON" or "OFF"
                supd = update == 1 and "ON" or "OFF"

                self.add_action(
                    name="[COLOR=FF66CC00][B][ + ][/B][/COLOR] " + path +
                    " [COLOR=FFC0C0C0][recursive=" + srec +
                    " , update=" + supd + "][/COLOR]",
                    params=[("do", "rootclic"), ("rootpath", path),
                            ("viewmode", "view"), ("exclude", "0")],
                    # paramètres
                    action="rootfolders", # action
                    iconimage=join(PIC_PATH, "folder_paths.png"), # icone
                    # menucontextuel
                    contextmenu=[(common.getstring(30206),
                                  "Notification(TODO: scan folder,scan this folder now !,3000,%s)" % \
                                      join(home,"icon.png")),
                                 (common.getstring(30207),
                                  "Container.Update(\"%s?" % (sys.argv[0]) +
                                  "action=rootfolders&do=delroot&delpath=%s&exclude=1&viewmode=view\",)" % \
                                      (common.quote_param(path)))])

            # Add a folder to exclude
            if len(includefolders) >= 0:
                self.add_action(name=common.getstring(30211), # add a folder to exclude
                                params=[("do", "addroot"), ("viewmode","view"), 
                                        ("exclude", "1")], # paramètres
                                action="rootfolders",  # action
                                iconimage=join(PIC_PATH, "folder_paths.png"),  # icone
                                contextmenu=None)  # menucontextuel

            # Show excluded folders
            for path, recursive, update in excludefolders:
                self.add_action(name="[COLOR=FFFF0000][B][ - ][/B][/COLOR] " + path,
                                params=[("do", "rootclic"), ("rootpath", path),
                                        ("viewmode", "view"), ("exclude", "1")], # paramètres
                                action="rootfolders",  # action
                                iconimage=join(PIC_PATH, "folder_paths.png"),  # icone
                                # menucontextuel
                                contextmenu=[(common.getstring(30210),
                                              "Container.Update(\"%s?" % (sys.argv[0]) +
                                              "action=rootfolders&do=delroot&delpath=%s&exclude=0&viewmode=view\",)" % \
                                                  (common.quote_param(path)))])

            if self.args.do == "delroot":
                xbmcplugin.endOfDirectory(int(sys.argv[1]), updateListing=True)
            else:
                xbmcplugin.endOfDirectory(int(sys.argv[1]))

    def prettydate(self, dateformat, datetuple):
        """date string formater (see strftime format)
        
        Replace %a %A %b %B date string by the day/month names for the given date tuple
        """
        dateformat = dateformat.replace("%a", common.getstring(30005).split("|")[
            datetuple.tm_wday])  # replace %a marker by short day name
        dateformat = dateformat.replace("%A", common.getstring(30007).split("|")[
            datetuple.tm_wday])  # replace %A marker by long day name
        dateformat = dateformat.replace("%b", common.getstring(30006).split("|")[
            datetuple.tm_mon-1])  # replace %b marker by short month name
        dateformat = dateformat.replace("%B", common.getstring(30008).split("|")[
            datetuple.tm_mon-1])  # replace %B marker by long month name
        return dateformat

    def remove_period(self):

        MPDB.period_delete(self.args.periodname)
        xbmc.executebuiltin(
            "Container.Update(\"%s?action=showperiod&viewmode=view&period=''\" , replace)" % sys.argv[0])

    def period_rename(self):
        # TODO : test if 'datestart' is before 'dateend'
        periodname = urllib.parse.unquote_plus(self.args.periodname)
        datestart, dateend = \
            MPDB.cur.request_with_binds("""SELECT DateStart,DateEnd FROM Periodes WHERE PeriodeName=? """,
                                        (periodname,))[0]
        common.log("", "datestart = %s" % datestart)
        common.log("", "dateend = %s" % dateend)
        dialog = xbmcgui.Dialog()
        d = dialog.numeric(1, "Input start date for period",
                           strftime("%d/%m/%Y", strptime(str(datestart), "%Y-%m-%d %H:%M:%S")))
        datestart = strftime(
            "%Y-%m-%d", strptime(d.replace(" ", "0"), "%d/%m/%Y"))

        d = dialog.numeric(1, "Input end date for period",
                           strftime("%d/%m/%Y", strptime(str(dateend), "%Y-%m-%d %H:%M:%S")))
        dateend = strftime(
            "%Y-%m-%d", strptime(d.replace(" ", "0"), "%d/%m/%Y"))

        kb = xbmc.Keyboard(periodname, common.getstring(30110), False)
        kb.doModal()
        if (kb.isConfirmed()):
            titreperiode = kb.getText()
        else:
            titreperiode = periodname

        MPDB.period_rename(self.args.periodname,
                           titreperiode, datestart, dateend)
        xbmc.executebuiltin(
            "Container.Update(\"%s?action=showperiod&viewmode=view&period=''\" , replace)" % sys.argv[0])

    def collection_add_pic(self):
        listcollection = ["[[%s]]" % common.getstring(30157)] + [col[0] for col in MPDB.collections_list()]

        dialog = xbmcgui.Dialog()
        rets = dialog.select(common.getstring(30156), listcollection)
        if rets == -1:  # choix de liste annulé
            return
        if rets == 0:  # premier élément : ajout manuel d'une collection
            kb = xbmc.Keyboard("", common.getstring(30155), False)
            kb.doModal()
            if (kb.isConfirmed()):
                namecollection = kb.getText()
            else:
                # il faut traiter l'annulation
                return
            # 2 créé la collection en base
            MPDB.collection_new(namecollection)
        else:  # dans tous les autres cas, une collection existente choisie
            namecollection = listcollection[rets]
        # 3 associe en base l'id du fichier avec l'id de la collection
        path = self.args.path
        filename = self.args.filename

        MPDB.collection_add_pic(namecollection, path, filename)
        common.show_notification(common.getstring(30000), 
                                 common.getstring(30154) + ' ' + namecollection, 
                                 3000, join(home, "icon.png"))
        # xbmc.executebuiltin( "Notification(%s,%s %s,%s,%s)" % 
        # (common.getstring(30000),common.getstring(30154),namecollection,3000,join(home,"icon.png")))

    def collection_add_folder(self):
        listcollection = ["[[%s]]" % common.getstring(
            30157)] + [col[0] for col in MPDB.collections_list()]

        dialog = xbmcgui.Dialog()
        rets = dialog.select(common.getstring(30156), listcollection)
        if rets == -1:  # cancel
            return
        if rets == 0:  # new collection
            kb = xbmc.Keyboard("", common.getstring(30155), False)
            kb.doModal()
            if (kb.isConfirmed()):
                namecollection = kb.getText()
            else:
                # cancel
                return
            common.log("", namecollection)
            MPDB.collection_new(namecollection)
        else:  # existing collection
            namecollection = listcollection[rets]

        # 3 associe en base l'id du fichier avec l'id de la collection
        filelist = self.show_pics()  # on récupère les photos correspondantes à la vue
        for path, filename in filelist:  # on les ajoute une par une
            MPDB.collection_add_pic(namecollection, path, filename)

        common.show_notification(common.getstring(30000),
                                 common.getstring(30161) % len(
                                     filelist) + ' ' + namecollection, 3000,
                                 join(home, "icon.png"))

    def collection_delete(self):
        dialog = xbmcgui.Dialog()

        if dialog.yesno(common.getstring(30150), common.getstring(30251) % self.args.collect):
            MPDB.collection_delete(self.args.collect)
            xbmc.executebuiltin("Container.Update(\"%s?" % (sys.argv[0]) +
                                "action=showcollection&viewmode=view&collect=''&method=show\" , replace)")

    def collection_rename(self):
        kb = xbmc.Keyboard(self.args.collect, common.getstring(30153), False)
        kb.doModal()
        if (kb.isConfirmed()):
            newname = kb.getText()
        else:
            newname = self.args.collect
        MPDB.collection_rename(self.args.collect, newname)
        xbmc.executebuiltin("Container.Update(\"%s?" % (sys.argv[0]) +
                            "action=showcollection&viewmode=view&collect=''&method=show\" , replace)")

    def collection_add_playlist(self):
        ''' Purpose: launch Select Window populated with music playlists '''
        colname = self.args.collect
        common.log("", "collection_add_playlist")
        try:
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory", "params": {"directory": "special://musicplaylists/", "media": "music"}}')
            playlist_files = eval(result)['result']['files']
        except:
            return

        if playlist_files != None:

            plist_files = dict((x['label'], x['file']) for x in playlist_files)
            common.log("", plist_files)
            playlist_list = plist_files.keys()

            playlist_list.sort()
            inputchoice = xbmcgui.Dialog().select(common.getstring(30148), playlist_list)
            if inputchoice > -1:
                MPDB.collection_add_playlist(
                    self.args.collect, plist_files[playlist_list[inputchoice]])
            else:
                MPDB.collection_add_playlist(self.args.collect, '')

    def collection_del_pic(self):
        MPDB.collection_del_pic(
            self.args.collect, self.args.path, self.args.filename)
        xbmc.executebuiltin(
            "Container.Update(\"%s?" % (sys.argv[0]) +
            "action=showpics&viewmode=view&page=1&collect=%s&method=collection\" , replace)" % \
                (common.quote_param(self.args.collect)), )

    def show_diaporama(self):
        # 1- récupère la liste des images (en utilisant show_pics avec le bon paramètre
        self.args.viewmode = "diapo"
        self.args.page = ""
        self.show_pics()

    def show_lastshots(self):
        # récupère X dernières photos puis affiche le résultat
        pass

    # MikeBZH44 : Method to execute query
    def exec_query(self, query):
        # Execute query
        # Needed to store results if CommonCache cacheFunction is used
        _results = MPDB.cur.request(query)
        return _results

    # MikeBZH44 : Method to query database and store result in Windows properties and CommonCache table
    def set_properties(self):
        # Init variables
        _limit = m.args.limit
        _method = m.args.method
        _results = []
        _count = 0
        WINDOW = xbmcgui.Window(10000)
        START_TIME = time.time()
        # Get general statistics and set properties
        Count = MPDB.cur.request(
            """SELECT COUNT(*) FROM Files WHERE ImageDateTime IS NOT NULL""")[0]
        Collections = MPDB.cur.request(
            """SELECT COUNT(*) FROM Collections""")[0]
        Categories = MPDB.cur.request(
            """select count(distinct tf.idFile) from TagTypes tt, TagContents tc, TagsInFiles tf
               where tt.idTagType = tc.idTagType and tc.idTagContent = tf.idTagContent 
               and tt.TagTranslation = (select TagTranslation from TagTypes tti where tti.TagType='Category')""")[0]
        Folders = MPDB.cur.request(
            """SELECT COUNT(*) FROM Folders WHERE HasPics = 1""")[0]
        WINDOW.clearProperty("MyPicsDB%s.Count" % (_method))
        WINDOW.setProperty("MyPicsDB%s.Count" % (_method), str(Count[0]))
        WINDOW.clearProperty("MyPicsDB%s.Categories" % (_method))
        WINDOW.setProperty("MyPicsDB%s.Categories" %
                           (_method), str(Categories[0]))
        WINDOW.clearProperty("MyPicsDB%s.Collections" % (_method))
        WINDOW.setProperty("MyPicsDB%s.Collections" %
                           (_method), str(Collections[0]))
        WINDOW.clearProperty("MyPicsDB%s.Folders" % (_method))
        WINDOW.setProperty("MyPicsDB%s.Folders" % (_method), str(Folders[0]))
        # Build query string
        _query =  """SELECT b.FolderName, a.strPath, a.strFilename, ImageDateTime, TagContent """
        _query += """FROM Files AS a """
        _query += """     INNER JOIN Folders AS b """
        _query += """     ON a.idFolder = b.idFolder """
        _query += """     LEFT OUTER JOIN (SELECT a.idFile, a.idTagContent, b.TagContent """
        _query += """                      FROM TagsInFiles AS a, TagContents AS b, TagTypes AS c """
        _query += """                      WHERE a.idTagContent = b.idTagContent """
        _query += """                        AND b.idtagType = c.idTagType """
        _query += """                        AND c.tagType = 'Caption/abstract' """
        _query += """                     ) AS c """
        _query += """     ON a.idFile = c.idFile """
        _query += """WHERE ImageDateTime IS NOT NULL """
        if _method == "Latest":
            # Get latest pictures based on shooted date time or added date time
            _sort = m.args.sort
            if _sort == "Shooted":
                _query += """ORDER BY ImageDateTime DESC LIMIT %s""" % (
                    str(_limit))
            if _sort == "Added":
                _query += """ORDER BY "DateAdded" DESC LIMIT %s""" % (
                    str(_limit))
        if _method == "Random":
            # Get random pictures from database
            if MPDB.db_backend.lower() == 'mysql':
                _query += """ORDER BY RAND() LIMIT %s""" % (str(_limit))
            else:
                _query += """ORDER BY RANDOM() LIMIT %s""" % (str(_limit))
        # Request database
        _results = self.exec_query(_query)
        cache.table_name = "MyPicsDB"
        # Go through results
        for _picture in _results:
            _count += 1
            # Clean and set properties
            _path = join(_picture[1], _picture[2])
            WINDOW.clearProperty("MyPicsDB%s.%d.Folder" % (_method, _count))
            WINDOW.setProperty("MyPicsDB%s.%d.Folder" %
                               (_method, _count), _picture[0])
            WINDOW.clearProperty("MyPicsDB%s.%d.Path" % (_method, _count))
            WINDOW.setProperty("MyPicsDB%s.%d.Path" % (_method, _count), _path)
            WINDOW.clearProperty("MyPicsDB%s.%d.Name" % (_method, _count))
            WINDOW.setProperty("MyPicsDB%s.%d.Name" %
                               (_method, _count), _picture[2])
            WINDOW.clearProperty("MyPicsDB%s.%d.Date" % (_method, _count))
            WINDOW.setProperty("MyPicsDB%s.%d.Date" %
                               (_method, _count), _picture[3])
            WINDOW.clearProperty("MyPicsDB%s.%d.Comment" % (_method, _count))
            WINDOW.setProperty("MyPicsDB%s.%d.Comment" %
                               (_method, _count), _picture[4])
            # Store path into CommonCache
            cache.set("MyPicsDB%s.%d" % (_method, _count), (_path))
        # Store number of pictures fetched into CommonCache
        cache.set("MyPicsDB%s.Nb" % (_method), str(_count))
        # Result contain less than _limit pictures, clean extra properties
        if _count < _limit:
            for _i in range(_count + 1, _limit + 1):
                WINDOW.clearProperty("MyPicsDB%s.%d.Folder" % (_method, _i))
                WINDOW.clearProperty("MyPicsDB%s.%d.Path" % (_method, _i))
                cache.set("MyPicsDB%s.%d" % (_method, _i), "")
                WINDOW.clearProperty("MyPicsDB%s.%d.Name" % (_method, _i))
                WINDOW.clearProperty("MyPicsDB%s.%d.Date" % (_method, _i))
                WINDOW.clearProperty("MyPicsDB%s.%d.Comment" % (_method, _i))
        # Display execution time
        t = (time.time() - START_TIME)
        if t >= 60:
            return "%.3fm" % (t / 60.0)
        common.log("set_properties",
                   "Function set_properties took %.3f s" % (t))

    # MikeBZH44 : Method to get pictures from CommonCache and start slideshow
    def set_slideshow(self):
        # Init variables
        _current = m.args.current
        _method = m.args.method
        START_TIME = time.time()
        # Clear current photo playlist
        _json_query = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Playlist.Clear", "params": {"playlistid": 2}, "id": 1}')
        #_json_query = unicode(_json_query, 'utf-8', errors='ignore')
        _json_pl_response = simplejson.loads(_json_query)
        # Get number of picture to display from CommonCache
        cache.table_name = "MyPicsDB"
        _limit = int(cache.get("MyPicsDB%s.Nb" % (_method)))
        # Add pictures to slideshow, start from _current position
        for _i in range(_current, _limit + 1):
            # Get path from CommonCache for current picture
            _path = cache.get("MyPicsDB%s.%d" % (_method, _i))
            # Add current picture to slideshow
            _json_query = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Playlist.Add", "params": {"playlistid": 2, "item": {"file" : "%s"}}, "id": 1}' % (
                    str(_path.encode('utf8')).replace("\\", "\\\\")))
            #_json_query = unicode(_json_query, 'utf-8', errors='ignore')
            _json_pl_response = simplejson.loads(_json_query)
        # If _current not equal 1 then add pictures from 1 to _current - 1
        if _current != 1:
            for _i in range(1, _current):
                # Get path from CommonCache for current picture
                _path = cache.get("MyPicsDB%s.%d" % (_method, _i))
                # Add current picture to slideshow
                _json_query = xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "Playlist.Add", "params": {"playlistid": 2, "item": {"file" : "%s"}}, "id": 1}' % (
                        str(_path.encode('utf8')).replace("\\", "\\\\")))
                #_json_query = unicode(_json_query, 'utf-8', errors='ignore')
                _json_pl_response = simplejson.loads(_json_query)
        # Start Slideshow
        _json_query = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Player.Open", "params": {"item": {"playlistid": 2}}, "id": 1}')
        #_json_query = unicode(_json_query, 'utf-8', errors='ignore')
        _json_pl_response = simplejson.loads(_json_query)
        t = (time.time() - START_TIME)
        # Display execution time
        if t >= 60:
            return "%.3fm" % (t / 60.0)
        common.log("set_slideshow", "Function set_slideshow took %.3f s" % (t))

    def show_pics(self):

        if int(common.getaddon_setting("ratingmini")) > 0:
            min_rating = int(common.getaddon_setting("ratingmini"))
        else:
            min_rating = 0

        if not self.args.page:  # 0 ou "" ou None : pas de pagination ; on affiche toutes les photos de la requête sans limite
            page = 0
            limit = -1  # SQL 'LIMIT' statement equals to -1 returns all resulting rows
            offset = -1  # SQL 'OFFSET' statement equals to -1  : return resulting rows with no offset
        else:  # do pagination stuff
            page = int(self.args.page)
            limit = int(common.getaddon_setting("picsperpage"))
            offset = (page - 1) * limit

        if self.args.method == "folder":  # NON UTILISE : l'affichage par dossiers affiche de lui même les photos
            pass

        elif self.args.method == "wizard_settings":
            filelist = MPDB.filterwizard_get_pics_from_filter(
                self.args.filtername, min_rating)

        # we are showing pictures for a RANDOM selection
        elif self.args.method == "random":

            limit = int(common.getaddon_setting("randompicsnumber"))
            if limit < 10:
                limit = 10

            try:
                count = [row for row in MPDB.cur.request(
                    """SELECT count(*) 
                       FROM Files 
                       WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= ?""",
                    (min_rating,))][0][0]
            except:
                count = 0

            modulo = float(count) / float(limit)

            if MPDB.db_backend.lower() == 'mysql':
                filelist = [row for row in MPDB.cur.request(
                    """SELECT strPath, strFilename FROM Files 
                       WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= ? 
                       ORDER BY RAND() LIMIT %s OFFSET %s""" % (limit, offset), (min_rating,))]
            else:
                if count < limit:
                    select = """SELECT strPath, strFilename FROM Files 
                                WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= '%s' 
                                ORDER BY RANDOM() LIMIT %s OFFSET %s""" % (min_rating, limit, offset)
                else:
                    select = """SELECT strPath, strFilename FROM Files 
                                WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= '%s' 
                                AND RANDOM() %% %s 
                                ORDER BY RANDOM() LIMIT %s OFFSET %s""" % (min_rating, modulo, limit, offset)
                filelist = [row for row in MPDB.cur.request(select)]
                # remove video files, if parameter 'onlypics' is set
                if self.args.onlypics == "oui":
                    for path, filename in filelist:
                        if self.is_video(filename):
                            filelist.remove([path, filename])
                            #common.log("Main.show_pics", '%s' % str(filelist), xbmc.LOGINFO)
                
        # we are showing pictures for a DATE selection
        elif self.args.method == "date":
            #   lister les images pour une date donnée
            formatstring =  {"wo": "", 
                             "year": "%Y", 
                             "month": "%Y-%m", 
                             "date": "%Y-%m-%d", 
                             "": "%Y", 
                             "period": "%Y-%m-%d"}[self.args.period]

            if self.args.period == "wo":
                filelist = MPDB.get_all_files_wo_date(min_rating)

            elif self.args.period == "year" or self.args.period == "":
                if self.args.value:
                    filelist = MPDB.pics_for_period('year', self.args.value, min_rating)
                else:
                    filelist = MPDB.search_all_dates(min_rating)

            elif self.args.period in ["month", "date"]:
                filelist = MPDB.pics_for_period(self.args.period, self.args.value, min_rating)

            elif self.args.period == "period":
                filelist = MPDB.search_between_dates(DateStart=(self.args.datestart, formatstring),
                                                     DateEnd=(self.args.dateend, formatstring), 
                                                     MinRating=min_rating)
            else:  # period not recognized, show whole pics : TODO check if useful and if it can not be optimized for something better
                listyears = MPDB.get_years()
                amini = min(listyears)
                amaxi = max(listyears)
                if amini and amaxi:
                    filelist = MPDB.search_between_dates(("%s" % (amini), formatstring), 
                                                         ("%s" % (amaxi), formatstring),
                                                          MinRating=min_rating)
                else:
                    filelist = []

        # we are showing pictures for a TAG selection
        elif self.args.method == "wizard":
            filelist = MPDB.filterwizard_result(self.args.kw, self.args.nkw, self.args.matchall, 
                                                self.args.start, self.args.end, min_rating)

        # we are showing pictures for a TAG selection
        elif self.args.method == "tag":
            if not self.args.tag:  # p_category
                filelist = MPDB.search_tag(None)
            else:
                filelist = MPDB.search_tag(self.args.tag, self.args.tagtype)

        # we are showing pictures for a FOLDER selection
        elif self.args.method == "folders":
            folderid =int(self.args.folderid)
            listid = [folderid] + MPDB.all_children_of_folder(self.args.folderid)
            _query = """
                SELECT p.FullPath, f.strFilename FROM Files f, Folders p 
                WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= ? 
                AND p.idFolder in ('%s') AND f.idFolder=p.idFolder 
                ORDER BY ImageDateTime ASC 
                LIMIT %s OFFSET %s""" % ("','".join([str(i) for i in listid]), limit, offset)            
            filelist = [row for row in MPDB.cur.request(_query, (min_rating,))]

        elif self.args.method == "collection":
            if int(common.getaddon_setting("ratingmini")) > 0:
                min_rating = int(common.getaddon_setting("ratingmini"))
            else:
                min_rating = 0
            filelist = MPDB.collection_get_pics(self.args.collect, min_rating)
            common.log("show_pics", "method collection called, filelistL %s" % (filelist))

        elif self.args.method == "search":
            if int(common.getaddon_setting("ratingmini")) > 0:
                min_rating = int(common.getaddon_setting("ratingmini"))
            else:
                min_rating = 0
            filelist = MPDB.search_in_files(
                self.args.field, self.args.searchterm, min_rating, count=False)

        elif self.args.method == "lastmonth":
            # show pics taken within last month
            if MPDB.con.get_backend() == "mysql":
                filelist = [row for row in MPDB.cur.request(
                    """SELECT strPath,strFilename FROM Files 
                       WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= ? 
                       AND datetime(ImageDateTime) BETWEEN SysDate() - INTERVAL 1 MONTH AND SysDate() 
                       ORDER BY ImageDateTime ASC 
                       LIMIT %s OFFSET %s""" % (limit, offset), (min_rating,))]
            else:
                filelist = [row for row in MPDB.cur.request(
                    """SELECT strPath,strFilename FROM Files 
                       WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= ? 
                       AND datetime(ImageDateTime) BETWEEN datetime('now','-1 months') AND datetime('now') 
                       ORDER BY ImageDateTime ASC 
                       LIMIT %s OFFSET %s""" % (limit, offset), (min_rating,))]

        elif self.args.method == "recentpicsdb":  # pictures added to database within x last days __OK
            numberofdays = common.getaddon_setting("recentnbdays")
            if MPDB.con.get_backend() == "mysql":
                filelist = [row for row in MPDB.cur.request(
                    """SELECT strPath,strFilename FROM Files 
                       WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= ? 
                       AND DateAdded>=SysDate() - INTERVAL %s DAY 
                       ORDER BY DateAdded ASC 
                       LIMIT %s OFFSET %s""" % (numberofdays, limit, offset), (min_rating,))]
            else:
                filelist = [row for row in MPDB.cur.request(
                    """SELECT strPath,strFilename FROM Files 
                       WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= ? 
                       AND DateAdded >= datetime('now','start of day','-%s days') 
                       ORDER BY DateAdded ASC 
                       LIMIT %s OFFSET %s""" % (numberofdays, limit, offset), (min_rating,))]

        elif self.args.method == "lastpicsshooted":  # X last pictures shooted __OK
            select = """SELECT strPath,strFilename FROM Files 
                        WHERE COALESCE(case ImageRating when '' then '0' else ImageRating end,'0') >= '%s' 
                        AND ImageDateTime IS NOT NULL ORDER BY ImageDateTime DESC 
                        LIMIT %s""" % (min_rating, common.getaddon_setting('lastpicsnumber'))
            filelist = [row for row in MPDB.cur.request(select)]

        elif self.args.method == "videos":  # show all videos __OK
            filelist = [row for row in MPDB.cur.request(
                """SELECT strPath,strFilename FROM Files 
                WHERE ftype="video" ORDER BY ImageDateTime DESC 
                LIMIT %s OFFSET %s""" % (limit, offset))]

        # on teste l'argumen 'viewmode'
        # si viewmode = view : on liste les images
        # si viewmode = scan : on liste les photos qu'on retourne
        # si viewmode = zip  : on liste les photos qu'on zip
        # si viewmode = slideshow: on liste les photos qu'on ajoute au diaporama
        if self.args.viewmode == "scan":
            return filelist
        if self.args.viewmode == "slideshow":

            playlist_ondisk = MPDB.collection_get_playlist(self.args.collect)

            if playlist_ondisk is not None and len(playlist_ondisk) > 0:
                playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
                playlist.clear()
                playlist.add(playlist_ondisk)

                xbmc.Player().play(playlist)
                xbmc.executebuiltin("PlayerControl(RepeatAll)")
            command = "SlideShow(%s?action=showpics&method=collection&viewmode=view&collect=%s&name=%s, notrandom) " % (
                sys.argv[0], self.args.collect, self.args.collect)
            xbmc.executebuiltin(command)
            return

        if self.args.viewmode == "zip":
            from tarfile import open as taropen
            # TODO : enable user to select the destination
            destination = join(DATA_PATH, self.args.name + ".tar.gz")
            destination = xbmcvfs.translatePath(destination)

            if isfile(destination):
                dialog = xbmcgui.Dialog()
                ok = dialog.yesno(common.getstring(30000), common.getstring(30064) % basename(destination),
                                  dirname(destination), common.getstring(30065))  # Archive already exists, overwrite ?
                if not ok:
                    # todo, ask for another name and if cancel, cancel the zip process as well
                    common.show_notification(common.getstring(30000), common.getstring(30066), 
                                             3000, join(home, "icon.png"))
                    # xbmc.executebuiltin("Notification(%s,%s,%s,%s)"%(common.getstring(30000),common.getstring(30066),3000,join(home,"icon.png")))
                    return
                else:
                    pass  # user is ok to overwrite, let's go on
            
            # open a tar file using gz compression
            tar = taropen(destination.encode(sys.getfilesystemencoding()), mode="w:gz")
            error = 0
            pDialog = xbmcgui.DialogProgress()
            pDialog.create(common.getstring(30000),
                           common.getstring(30063), '')
            compte = 0
            msg = ""
            for (path, filename) in filelist:
                compte = compte + 1
                picture = join(path, filename)
                arcroot = path.replace(dirname(picture), "")
                arcname = join(arcroot, filename).replace("\\", "/")
                if picture == destination:  # sert à rien de zipper le zip lui même :D
                    continue
                pDialog.update(int(100 * (compte / float(len(filelist)))), 
                               common.getstring(30067), picture)  # adding picture to the archive
                try:
                    # Dirty hack for windows. 7Zip uses codepage cp850
                    if RunningOS == 'win32':
                        enc = 'cp850'
                    else:
                        enc = 'utf-8'
                    tar.add(picture.encode(sys_encoding), arcname.encode(enc))
                except:
                    common.log("show_pics >> zip",
                               "tar.gz compression error :", xbmc.LOGERROR)
                    error += 1
                    common.log("show_pics >> zip", 
                               "Error  %s" % arcname.encode(sys_encoding), xbmc.LOGERROR)
                    print_exc()
                if pDialog.iscanceled():
                    # Zip file has been canceled !
                    msg = common.getstring(30068)
                    break
            tar.close()
            if not msg:
                if error:
                    # "%s Errors while zipping %s files"
                    msg = common.getstring(30069) % (error, len(filelist))
                else:
                    # %s files successfully Zipped !!
                    msg = common.getstring(30070) % len(filelist)
            common.show_notification(common.getstring(
                30000), msg, 3000, join(home, "icon.png"))
            return

        if self.args.viewmode == "export":
            # 1- ask for destination
            dialog = xbmcgui.Dialog()
            # Choose the destination for exported pictures
            dstpath = dialog.browse(3, common.getstring(30180), "files", "", True, False, "")
            if dstpath == "":
                return

            ok = dialog.yesno(common.getstring(30000), common.getstring(30181),
                              "(%s)" % self.args.name)  # do you want to create a folder for exported pictures ?
            if ok:
                dirok = False
                while not dirok:
                    kb = xbmc.Keyboard(self.args.name, common.getstring(
                        30182), False)  # Input subfolder name
                    kb.doModal()

                    if (kb.isConfirmed()):
                        subfolder = kb.getText()
                        try:
                            os.mkdir(join(dstpath, subfolder))
                            dstpath = join(dstpath, subfolder)
                            dirok = True
                        except Exception as msg:
                            print_exc()
                            dialog.ok(common.getstring(30000),
                                      "Error#%s : %s" % msg.args)
                    else:
                        common.show_notification(common.getstring(30000), common.getstring(30183), 3000,
                                                 join(home, "icon.png"))
                        return

            from shutil import copy
            pDialog = xbmcgui.DialogProgress()
            # 'Copying files...')
            pDialog.create(common.getstring(30000), common.getstring(30184))
            i = 0.0
            cpt = 0
            for path, filename in filelist:
                pDialog.update(int(100 * i / len(filelist)), 
                               common.getstring(30185) % join(path, filename),
                               dstpath)  # "Copying '%s' to :"
                i = i + 1.0
                if isfile(join(dstpath, filename)):
                    ok = dialog.yesno(common.getstring(30000), 
                                      common.getstring(30186) % filename, dstpath,
                                      common.getstring(30187))  # File %s already exists in... overwrite ?
                    if not ok:
                        continue
                copy(join(path, filename), dstpath)
                cpt = cpt + 1
            pDialog.update(100, common.getstring(30188),
                           dstpath)  # "Copying Finished !
            xbmc.sleep(1000)
            common.show_notification(common.getstring(30000), 
                                     common.getstring(30189) % (cpt, dstpath), 3000,
                                     join(home, "icon.png"))
            # show the folder which contain pictures exported
            dialog.browse(2, common.getstring(30188), "files", "", True, False, dstpath) 
            return

        if len(filelist) >= limit:
            if int(page) > 1:
                common.log("show_pics >> pagination",
                           "TODO  : display previous page item")
            if (page * limit) < (len(filelist)):
                common.log("show_pics >> pagination",
                           "TODO  : display next page item")

        # fill the pictures list
        count = 0
        for path, filename in filelist:
            context = []
            count += 1
            # - add to collection
            context.append((common.getstring(30152),
                            "RunPlugin(\"%s?" % (sys.argv[0]) +
                            "action=addtocollection&viewmode=view&path=%s&filename=%s\")" % \
                                (common.quote_param(path), common.quote_param(filename))))
            # - del pic from collection :
            if self.args.method == "collection":
                context.append((common.getstring(30151),
                                "RunPlugin(\"%s?" % (sys.argv[0]) +
                                "action=delfromcollection&viewmode=view&collect=%s&path=%s&filename=%s\")" % \
                                    (common.quote_param(self.args.collect),
                                     common.quote_param(path),
                                     common.quote_param(filename))))
            # 3 -
            context.append((common.getstring(30060),
                            "RunPlugin(\"%s?" % (sys.argv[0]) +
                            "action=locate&filepath=%s&viewmode=view\" ,)" % \
                                (common.quote_param(join(path, filename)))))

            # 5 - infos
            # context.append( ( "paramètres de l'addon","ActivateWindow(virtualkeyboard)" ) )
            self.add_picture(filename,
                             path,
                             count=count,
                             contextmenu=context,
                             fanart=self.find_fanart(path, filename))
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_PROGRAM_COUNT)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)

        self.change_view()

        xbmcplugin.endOfDirectory(int(sys.argv[1]))


GlobalFilterTrue = []
GlobalFilterFalse = []
GlobalMatchAll = 0
g_start_date = ''
g_end_date = ''
Handle = 0


def filterwizard_delegate(ArrayTrue, ArrayFalse, MatchAll=0, start_date='', end_date=''):
    global GlobalFilterTrue, GlobalFilterFalse, GlobalMatchAll, Handle, g_start_date, g_end_date
    GlobalFilterTrue = ArrayTrue
    GlobalFilterFalse = ArrayFalse
    GlobalMatchAll = MatchAll
    g_start_date = start_date
    g_end_date = end_date
    Handle = int(sys.argv[1])


if __name__ == "__main__":

    m = Main()
    MPDB = MypicsDB.MyPictureDB()

    if not sys.argv[2] or len(sys.argv[2]) == 0:

        if common.getaddon_setting("initDB") == "true":
            MPDB.make_new_base(True)
            common.setaddon_setting("initDB", "false")
        else:
            MPDB.version_table()

        if common.getaddon_setting('bootscan') == 'true':
            if common.getaddon_setting('scanning') == 'false':
                common.run_script("%s, --database" % "script.module.mypicsdb2scan")
                xbmc.executebuiltin(
                    "Container.Update(\"%s?action=showhome&viewmode=view\" ,)" % (sys.argv[0]),)
        else:
            m.show_home()

    elif m.args.action == 'scan':
        m.show_home()

    elif m.args.action == 'showhome':
        m.show_home()

    elif m.args.action == 'showdate':
        m.show_date()

    elif m.args.action == 'showfolder':
        m.show_folders()

    elif m.args.action == 'showkeywords':
        m.show_keywords()

    elif m.args.action == "showtranslationeditor":
        m.show_translationeditor()

    elif m.args.action == "help":
        m.show_help()

    elif m.args.action == 'showwizard':
        m.show_wizard()

    elif m.args.action == 'showtagtypes':
        m.show_tagtypes()

    elif m.args.action == 'showtags':
        m.show_tags()

    elif m.args.action == 'showpics':
        m.show_pics()

    elif m.args.action == 'showperiod':
        m.show_period()

    elif m.args.action == 'removeperiod':
        m.remove_period()

    elif m.args.action == 'renameperiod':
        m.period_rename()

    elif m.args.action == 'showcollection':
        m.show_collection()

    elif m.args.action == 'addtocollection':
        m.collection_add_pic()

    elif m.args.action == 'removecollection':
        m.collection_delete()

    elif m.args.action == 'delfromcollection':
        m.collection_del_pic()

    elif m.args.action == 'renamecollection':
        m.collection_rename()

    elif m.args.action == 'globalsearch':
        m.global_search()

    elif m.args.action == 'collectionaddplaylist':
        m.collection_add_playlist()

    elif m.args.action == 'addfolder':
        m.collection_add_folder()

    elif m.args.action == 'rootfolders':
        m.show_roots()

    elif m.args.action == 'showsettings':
        m.show_settings()

    elif m.args.action == 'locate':
        dialog = xbmcgui.Dialog()
        dstpath = dialog.browse(2, common.getstring(30071), "files", "", True, False, m.args.filepath)

    elif m.args.action == 'geolocate':
        m.show_map()

    elif m.args.action == 'diapo':
        pass
        # m.show_diaporama()

    elif m.args.action == 'alea':
        # TODO : afficher une liste aléatoire de photos
        pass
    elif m.args.action == 'lastshot':
        m.show_lastshots()

    elif m.args.action == 'request':
        pass

    # MikeBZH44 : Method to query database and store result in Windows properties and CommonCache table
    elif m.args.action == 'setproperties':
        m.set_properties()

    # MikeBZH44 : Method to get pictures from CommonCache and start slideshow
    elif m.args.action == 'slideshow':
        m.set_slideshow()
    else:
        m.show_home()

    try:
        MPDB.cur.close()
        MPDB.con.disconnect()
    except:
        pass
        
    del MPDB
