from django.db.models.fields.files import ImageField,ImageFieldFile
try:
    from PIL import Image
except:
    import Image
import os
IMG_MAX_WIDTH=100
IMG_MAX_HEIGHT=100

def _add_thumb(s,fix="thumb"):
    """
    Modifies a string (filename,URL) containing an image filename,to insert
    '.thumb' before the file extension (which is changed to be '.jpg')
    """
    parts=s.split(".")
    parts.insert(-1,fix)
    if parts[-1].lower() not in ['jpeg','jpg','png']:
        parts[-1]='jpg'
    return ".".join(parts)

class ThumbnailImageFieldFile(ImageFieldFile):
    def _get_thumb_path(self):
        return _add_thumb(self.path)
    
    thumb_path=property(_get_thumb_path)

    def _get_thumb_url(self):
        return _add_thumb(self.url)
    
    thumb_url=property(_get_thumb_url)
    
    def _get_thumb_big_path(self):
        return _add_thumb(self.path,"thumb_big")
    
    thumb_big_path=property(_get_thumb_big_path)

    def _get_thumb_big_url(self):
        return _add_thumb(self.url,"thumb_big")
    
    thumb_big_url=property(_get_thumb_big_url)

    def save(self,name,content,save=True):
        super(ThumbnailImageFieldFile,self).save(name,content,save)
        img=Image.open(self.path).convert('RGB')
        img.thumbnail(
            (self.field.thumb_width,self.field.thumb_height),
            Image.ANTIALIAS
        )
        img.save(self.thumb_path)
        
        img=Image.open(self.path).convert('RGB')   
        img=img.resize(
            (IMG_MAX_WIDTH,IMG_MAX_HEIGHT),
            Image.ANTIALIAS
        )
        img.save(self.thumb_big_path)

    def delete(self,save=True):
        if os.path.exists(self.thumb_path):
            os.remove(self.thumb_path)
        if os.path.exists(self.thumb_big_path):
            os.remove(self.thumb_big_path)
        super(ThumbnailImageFieldFile.self).delete(save)

class ThumbnailImageField(ImageField):
    """
    Behaves like a regular ImageField,but stores an extra (JPEG) thumbnail
    image,providing get_FIELD_thumb_url() and get_FIELD_thumb_filename().
    Accepts two additional,optional arguments:thumb_width and thumb_height,
    both defaulting to 128px,Resizing will preserve aspect ratio while
    staying inside the requested dismensions;see PIL's Image.thumbnail()
    method doc for details.
    """
    attr_class=ThumbnailImageFieldFile
    
    def __init__(self,thumb_width=14,thumb_height=14,*args,**kwargs):
        self.thumb_width=thumb_width
        self.thumb_height=thumb_height
        super(ThumbnailImageField,self).__init__(*args,**kwargs)

