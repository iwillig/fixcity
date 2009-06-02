from django.contrib.gis.db import models
from django.forms import ModelForm


class  CommunityBoard(models.Model):
    gid = models.IntegerField(primary_key=True)
    borocd = models.IntegerField()
    name = models.CharField(max_length=10)
    the_geom = models.MultiPolygonField()
    objects = models.GeoManager()

    class Meta:
        db_table = u'gis_community_board'
        ordering = ['name']

    def __unicode__(self):
        return "Brooklyn Communtiy Board %s " % self.name




class Rack(models.Model): 
    address = models.CharField(max_length=200)
    title = models.CharField(max_length=50)
    date = models.DateTimeField()    
    description = models.TextField(blank=True)
    email = models.EmailField()
    STATUS_STATE  = ( 
        ('suggest', 'suggest'),
        ('assessing', 'assessing'),
        ('assessed', 'assessed'),
        ('built','built'),
        ('rejected','rejected')                      
    )
    communityboard = models.ForeignKey(CommunityBoard)
    photo = models.ImageField(upload_to='images/racks/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_STATE)
    location = models.PointField(srid=4326)
    objects = models.GeoManager()

    class Meta:
        ordering = ['communityboard']

    def __unicode__(self):
        return self.address



class Rack_Document(models.Model): 
    file = models.FileField(upload_to='documents/', blank=True, null=True)
    contact_email = models.EmailField()
    doc_rack = models.ForeignKey(Rack)
        
    class Meta: 
        ordering = ['doc_rack']

    def __unicode__(self):
        return self.contact_email


class Rack_Photo(models.Model): 
    image = models.ImageField(upload_to='images/racks/', blank=True, null=True)
    contact_email = models.EmailField()
    ph_rack = models.ForeignKey(Rack)
        
    class Meta: 
        ordering = ['ph_rack']

    def __unicode__(self):
        return self.contact_email



class Comment(models.Model):
    text = models.TextField()
    contact_email = models.EmailField()
    rack = models.ForeignKey(Rack)
    
    class Meta: 
        ordering = ['rack']

    def __unicode__(self):
        return self.contact_email



class Neighborhoods(models.Model):
    gid = models.IntegerField(primary_key=True)
    state = models.CharField(max_length=2)
    county = models.CharField(max_length=43)
    city = models.CharField(max_length=64)
    name = models.CharField(max_length=64)
    regionid = models.IntegerField()
    the_geom = models.MultiPolygonField() 
    objects = models.GeoManager()

    class Meta:
        db_table = u'gis_neighborhoods'
        
    def __unicode__(self):
        return self.name


class SubwayStations(models.Model):
    gid = models.IntegerField(primary_key=True)
    objectid = models.TextField() # This field type is a guess.
    id = models.IntegerField()
    name = models.CharField(max_length=31)
    alt_name = models.CharField(max_length=38)
    cross_st = models.CharField(max_length=27)
    long_name = models.CharField(max_length=60)
    label = models.CharField(max_length=50)
    borough = models.CharField(max_length=15)
    nghbhd = models.CharField(max_length=30)
    routes = models.CharField(max_length=20)
    transfers = models.CharField(max_length=25)
    color = models.CharField(max_length=30)
    express = models.CharField(max_length=10)
    closed = models.CharField(max_length=10)
    the_geom = models.PointField()
    objects = models.GeoManager()
    class Meta:
        db_table = u'gis_subway_stations'




class RackForm(ModelForm): 
    class Meta: 
        model = Rack 

class CommentForm(ModelForm): 
    class Meta: 
        model = Comment
        

