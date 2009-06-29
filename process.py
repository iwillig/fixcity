from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData
from sqlalchemy.orm import mapper 
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


from sqlgeotypes import MULTIPOLYGON  


SRID=4326
Base = declarative_base()


engine = create_engine('postgres://postgres:hope@localhost:5432/gisdb')
connection = engine.connect() 


class Spatial_Ref(Base): 
    __tablename__ = 'spatial_ref_sys'

    srid = Column(Integer, primary_key=True)
    auth_name =  Column(String)
    auth_srid = Column(String) 
    srtext = Column(String) 
    proj4text = Column(String) 
    
    def __init__(self, auth_name, auth_srid, srtext, proj4text): 
        self.auth_name = auth_name 
        self.auth_srid = auth_srid 
        self.srtext = srtext 
        self.proj4text = proj4text 

spatial_ref = Spatial_Ref.__table__ 


class Communities(Base): 
    __tablename__ = "communities" 
    gid = Column(Integer, primary_key=True)
    borocode = Column(Integer)
    boroname = Column(String)
    countyfips = Column(String)
    pjareacode = Column(String)
    pjareaname = Column(String)
    shape_leng = Column(Integer)
    shape_area = Column(Integer)
    the_geom = Column(MULTIPOLYGON(SRID))
    

    def __init__(self,borocode,boroname,countyfips,pjareacode,pjareaname,shape_leng,shape_area,the_geom):
        self.borocode = borocode  
        self.boroname = boroname
        self.countyfips = countyfips
        self.pjareacode = pjareacode
        self.pjareaname = pjareaname
        self.shape_leng = shape_leng
        self.shape_area = shape_area
        self.the_geom = the_geom
        



class CommunityDistricts(Base): 
    __tablename__ = 'community_districts'    
    gid = Column(Integer, primary_key=True)
    borocd = Column(Integer) 
    shape_leng = Column(Integer) 
    shape_area = Column(Integer) 
    the_geom =   Column(MULTIPOLYGON(SRID))
    borough = Column(String)
    name = Column(String)

    def __init__(self, gid,borocd, boroname,shape_leng,shape_area,the_geom,borough,name): 
        self.borocd = borocd
        self.shape_leng = shape_leng 
        self.shape_area = shape_area 
        self.the_geom = the_geom 
        self.borough  = borough 
        self.name = name 

communities = Communities.__table__
communitydistricts = CommunityDistricts.__table__ 
metadata = Base.metadata 
metadata = MetaData()
Session = sessionmaker(bind=engine) 
session = Session()


# process the community districts 

def update():
    for feature in session.query(CommunityDistricts):
        id = str(feature.borocd)
        if id.startswith('1'):
            feature.borough = "Manhattan" 
            name = id.strip('1') 
            feature.name = name 
        if id.startswith('2'): 
            feature.borough = "Bronx" 
            name = id.strip('2') 
            feature.name = name
        if id.startswith('3'): 
            feature.borough = "Brooklyn" 
            name = id.strip('3') 
            feature.name = name
        if id.startswith('4'): 
            feature.borough = "Queens" 
            name = id.strip('4') 
            feature.name = name 
        if id.startswith('5'): 
            feature.borough = "Staten Island" 
            name = id.strip('5') 
            feature.name = name 
        session.flush()
        session.commit()


def communities():
    for dist in session.query(CommunityDistricts).filter(CommunityDistricts.gid == '1'):
#.filter(CommunityDistricts.the_geom.contains(Communities.the_geom)).\
        print dist.name
        

communities()
