# -*- coding: utf8 -*-
"""
Todo : Due to performance reasons RDF data is parsed by string functions. 
       Perhaps there is a fast xml parser library?
"""

import xbmc
import re
from os.path import join
import resources.lib.common as common
import html as HTMLParser

tag_set = {'MPReg:PersonDisplayName' : 'MPReg:PersonDisplayName',
           'Iptc4xmpExt:PersonInImage' : 'Iptc4xmpExt:PersonInImage', 
           'mwg-rs:RegionList:Face': 'mwg-rs:RegionList',

           'Iptc4xmpExt:City' : 'Iptc4xmpExt:City', 
           'Iptc4xmpExt:CountryName' : 'Iptc4xmpExt:CountryName', 
           'Iptc4xmpExt:CountryCode' : 'Iptc4xmpExt:CountryCode', 
           'Iptc4xmpExt:Sublocation' : 'Iptc4xmpExt:Sublocation', 
           'Iptc4xmpExt:Event' : 'Iptc4xmpExt:Event', 
           'Iptc4xmpExt:WorldRegion' : 'Iptc4xmpExt:WorldRegion', 
           'Iptc4xmpExt:ProvinceState' : 'Iptc4xmpExt:ProvinceState', 
           'Iptc4xmpExt:Event' : 'Iptc4xmpExt:Event', 

           'Iptc4xmpCore:Location' : 'Iptc4xmpCore:Location',
           'Iptc4xmpCore:City' : 'Iptc4xmpCore:City',
           'Iptc4xmpCore:Country' : 'Iptc4xmpCore:Country',
           'Iptc4xmpCore:CountryCode' : 'Iptc4xmpCore:CountryCode',
           'Iptc4xmpCore:Province-State' : 'Iptc4xmpCore:Province-State',
           'Iptc4xmpCore:Creator' : 'Iptc4xmpCore:Creator',
           'Iptc4xmpCore:DateCreated' : 'Iptc4xmpCore:DateCreated',
           'Iptc4xmpCore:Description' : 'Iptc4xmpCore:Description',
           'Iptc4xmpCore:DescriptionWriter' : 'Iptc4xmpCore:DescriptionWriter',
           'Iptc4xmpCore:Headline' : 'Iptc4xmpCore:Headline',
           'Iptc4xmpCore:Keywords' : 'Iptc4xmpCore:Keywords',
           'Iptc4xmpCore:Title' : 'Iptc4xmpCore:Title',

           'xmp:Label' : 'xmp:Label',
           'xmp:Rating' : 'xmp:Rating',
           'xap:Rating' : 'xap:Rating',

           'photoshop:Category' : 'photoshop:Category',
           'photoshop:City' : 'photoshop:City',
           'photoshop:Country' : 'photoshop:Country',
           'photoshop:DateCreated' : 'photoshop:DateCreated',
           'photoshop:Headline' : 'photoshop:Headline',
           'photoshop:State' : 'photoshop:State',
           'photoshop:SupplementalCategories' : 'photoshop:SupplementalCategories',
           'photoshop:Urgency' : 'photoshop:Urgency',
           'photoshop:Instructions' : 'photoshop:Instructions',
           'photoshop:CaptionWriter' : 'photoshop:CaptionWriter',

           'dc:creator' : 'dc:creator',
           'dc:description' : 'dc:description',
           'dc:rights' : 'dc:rights',
           'dc:subject' : 'dc:subject',
           'dc:title' : 'dc:title'}



class XMP_Tags(object):
    get_xmp_dirname = ''
    get_xmp_picfile = ''
    get_xmp_inner = ''
        
    def __get_xmp_metadata(self, dirname, picfile):
        
        #xmptag = 'x:xmpmeta'
        xmptag = 'rdf:RDF'

        self.get_xmp_dirname = dirname
        self.get_xmp_picfile = picfile
        
        try:
            f = open(join(dirname,picfile), 'rb')
        except:
            path = join(dirname,picfile)
            #path = common.smart_unicode(path).encode('utf-8')
            f = open(path, 'rb')
        content = str(f.read())
        f.close()

        #print "__get_xmp_metadata"
        start = content.find("<" + xmptag)
        end   = content.rfind("</" + xmptag) + 4 + len(xmptag)
        
        inner = content[start:end]
        self.get_xmp_inner = inner


            
    def get_xmp(self, dirname, picfile):
        ###############################
        #    getting  XMP   infos     #
        ###############################
        xmp = {}
        for storedtag, tagname in tag_set.items():
            #common.log("","Tag: " + tagname + " for " + picfile, xbmc.LOGINFO)
            #common.log("","storedtag: " + storedtag + " for " + picfile, xbmc.LOGINFO)
            if self.get_xmp_dirname != dirname or self.get_xmp_picfile != picfile:
                self.__get_xmp_metadata(dirname, picfile)

            start = self.get_xmp_inner.find("<" + tagname)
            end   = self.get_xmp_inner.rfind("</" + tagname) + 4 + len(tagname)
            inner = self.get_xmp_inner[start:end]
            
            #common.log("", "Innertag : " + inner, xbmc.LOGINFO)
            
            j = 0
            val_inner_tag=''
            if start != -1 and end != -1:
                end = inner.find("</" + tagname)
                while end != -1:

                    start = inner.find(">")+1
                    if start == 0:
                        break

                    tag_found = inner[start:end]
                    #common.log("","Found: Tag Name = " +  tagname, xbmc.LOGINFO)
                    #common.log("","Found: Tag Value = " +  tag_found, xbmc.LOGINFO)
                    #print tag_found
                    i = 0
                    val_inner_tag = ''
                    while i < len(tag_found):
                        if ord(tag_found[i])!=0:
                            val_inner_tag += tag_found[i]
                        i += 1

                    if len(val_inner_tag):
                        #common.log("","if len(val_inner_tag) ", xbmc.LOGINFO)
                        value = val_inner_tag
                        # find inner tags and delete them  <rdf:li[^>]*?>(.*?)</rdf:li>
                        matchouter=re.compile('<rdf:Alt[^>]*?>(.*?)</rdf:Alt>',re.DOTALL).findall(value)
                        #common.log("","after compile 1", xbmc.LOGINFO)
                        
                        if len(matchouter) == 0:
                            matchouter=re.compile('<rdf:Seq[^>]*?>(.*?)</rdf:Seq>',re.DOTALL).findall(value)
                            #common.log("","after compile 2", xbmc.LOGINFO)
                        if len(matchouter) == 0:
                            matchouter=re.compile('<rdf:Bag[^>]*?>(.*?)</rdf:Bag>',re.DOTALL).findall(value)
                            #common.log("","after compile 3", xbmc.LOGINFO)
                            
                        key = ''
                        
                        for outer in matchouter:
                            matchinner=re.compile('<rdf:li[^>]*?>(.*?)</rdf:li>',re.DOTALL).findall(outer)
                            #common.log("","after compile 4", xbmc.LOGINFO)
                            for inner in matchinner:
                                inner = inner.strip(' \t\n\r')
                                if len(inner) > 0:
                                    # Test for face in mwg-rs:RegionList
                                    if 'mwg-rs:RegionList' == tagname:
                                        faces=re.compile('<rdf:Description[^>]*?mwg-rs:Name="([^>]*?)"[^>]*?mwg-rs:Type="Face"[^>]*?>',re.DOTALL).findall(inner)
                                        for face in faces:
                                            if len(key) > 0:
                                                key += '||' + face
                                            else:
                                                key = face
                                        faces=re.compile('<rdf:Description[^>]*?mwg-rs:Type="Face"[^>]*?mwg-rs:Name="([^>]*?)"[^>]*?>',re.DOTALL).findall(inner)
                                        for face in faces:
                                            if len(key) > 0:
                                                key += '||' + face
                                            else:
                                                key = face
                                    else:
                                        if len(key) > 0:
                                            key += '||' + inner
                                        else:
                                            key = inner
                                    
                                value = key
                                
                        if len(value) > 0:
                            value = HTMLParser.unescape(value)
                            if storedtag in xmp:
                                xmp[storedtag] += '||' + value
                            else:
                                xmp[storedtag] = value

                    inner = inner[end+1:]
                    start = inner.find("<" + tagname)
                    inner = inner[start:]
                    end = inner.find("</" + tagname)
                    j = j+ 1
                    
            # XMP pictures tags are attributes of <rdf: ...
            else:
                start = self.get_xmp_inner.find(tagname+'="')
                end   = self.get_xmp_inner.rfind("</" + tagname) + 4 + len(tagname)
                inner = self.get_xmp_inner[start:]            
                #print "Notfound: Tag Name = " +  tagname
                matched=re.compile(tagname + '="(.*?)"',re.DOTALL).findall(inner)
                for value in matched:
                    value = value.strip(' \t\n\r')
                    if len(value) > 0:
                        #print "Found value = " + inner
                        if len(value) > 0:
                            value = HTMLParser.unescape(value)
                            if storedtag in xmp:
                                xmp[storedtag] += '||' + value
                            else:
                                xmp[storedtag] = value
            
        return xmp