from siyavula.models import *

tables = {}

# Have a tables dictionary that has all of the tables in it for easy (and generic) reference
# to them when trying to use metadata to loop through and access all of the tables.
for class_object in [
        Activity, Book, Cache, Chapter, Class, Concept, ConceptDependency, ConceptGroupHierarchy,
        Curriculum, Message, MessageType, Meta, NewSection, NewSectionConcept, NewSectionHierarchy,
        Project, Record, RecordHash, School, Section, Session, ShortCode, Task, Template,
        TemplateSection, TemplateNewSection, TemplateResponse, UserSchool, UserClass, Voucher,
        User, UserIdentifier, UserProfileGeneral, UserProfile, MemberService, OTP]:
    tables[class_object.__tablename__] = class_object
