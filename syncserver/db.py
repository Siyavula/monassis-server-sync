from siyavula.models import *

tables = {}

# Have a tables dictionary that has all of the tables in it for easy (and generic) reference
# to them when trying to use metadata to loop through and access all of the tables.
for class_object in [
        Cache, Class, Concept, ConceptDependency, ConceptGroupHierarchy, Meta, NewSection,
        NewSectionHierarchy, RecordHash, School, Session, Task, TemplateNewSection,
        TemplateResponse, UserSchool, UserClass, Project,
        User, UserIdentifier, UserProfileGeneral, UserProfile, MemberService, OTP]:
    tables[class_object.__tablename__] = class_object
