class fancyconfigparser(ConfigParser.RawConfigParser):
    def __init__(self, filename, sections=None):
        """
        File is  name.
        Sections is optional and will be used to create a new plate file
        from the data and write it to file on the first call of write
        """

        #Init the parser
        ConfigParser.RawConfigParser.__init__(self)
        #self.optionxform=str
        self.plate_filename=file
        
        if sections:
            self._load_from_data(sections)
        else:
            self._load_from_file(filename)
            #Load the file
            with open(self.plate_filename,'r') as configFile:
                try:
                    self.readfp(configFile)
                except ConfigParser.ParsingError as e:
                    raise InvalidPlate(str(e)+'\n')
            if self.has_option('Plate','std_offset'):
                self.set('Plate','offset',self.get('Plate','std_offset'))
                self.remove_option('Plate','std_offset')

        #If errors abort
        #errs=self._vet()
        errs=[]
        if errs:
            raise ConfigParser.ParsingError('\n'.join(errs))
    
    def _load_from_data(self,sections):
        """
        Sections is a dict with keys in REQUIRED_SECTIONS and with the 
        required setup subsections
        
        """
        #Define all the sections in the config file
        self.add_section('Plate')
        self.add_section('PlateHoles')
        for key in sections:
            if 'setup' in key.lower():
                section_key=key.replace(' ','')
                self.add_section(section_key)
                self.add_section(section_key+':Targets')
                self.add_section(section_key+':Guide')
                self.add_section(section_key+':Unused')
    
        #Plate section
        self._update_section('Plate',sections['plate'])
        self.set('Plate','formatversion','0.3')

        #Plate holes section
        recs=_dictlist_to_records(sections['plateholes'],
                                  PLATEHOLE_REQUIRED_COLS,
                                  PLATEHOLE_KEY)
        for r in recs:
            self.set('PlateHoles', *r)
        
        #Setup Sections
        for s in (k for k in sections if 'setup' in k.lower()):
            cannonical_setup_name=s.replace(' ','')
            self._init_setup_section(cannonical_setup_name, sections[s])

    def _init_setup_section(self, setup_name, setup_dict):
        """ 
        setup_dict should be a dict of lists of dicts
        with keys Info, Targets, Guide, & optionally Unused
        
        missing data will be replaced with -
        """
        #Add setup info
        
        attrib=setup_dict['info'].copy()
        #preprocess az,el & ra,de
        try:
            attrib['(az,el)']="({}, {})".format(attrib.pop('AZ'),
                                                attrib.pop('EL'))
        except KeyError:
            pass
        try:
            attrib['(ra,de)']="({}, {})".format(attrib.pop('RA'),
                                                attrib.pop('DE'))
        except KeyError:
            pass
        
        self._update_section(setup_name, attrib) #TODO determine key case
        
        ###Add target section###
        
        rec=_targ_dictlist_to_records(setup_dict['Targets'])
        for r in rec:
            self.set(setup_name+':Targets', *r)

        ###Add guide section###

        rec=_dictlist_to_records(setup_dict['Guide'],
                                 GUIDE_REQUIRED_COLS,
                                 GUIDE_KEY)
        for r in rec:
            self.set(setup_name+':Guide', *r)
            
        ###Add Unused section###
        
        if 'Unused' in setup_dict:
            rec=_dictlist_to_records(setup_dict['Unused'],
                                     UNUSED_REQUIRED_COLS,
                                     UNUSED_KEY)
            for r in rec:
                self.set(setup_name+':Unused', *r)

    def _update_section(self,section, d):
        for k,v in d.iteritems():
            self.set(section,str(k),str(v))
    
    def setup_sections(self):
        """Return setup section names only"""
        sec=[j for j in self.sections() if j[:5]=='Setup' and ':' not in j]
        return sorted(sec,key=lambda s: int(s[5:]))

    def target_sections(self):
        """Return setup target section names only"""
        return [j for j in self.sections() if j[:5]=='Setup' and ':Targets' in j]

    def guide_sections(self):
        """Return setup guide section names only"""
        return [j for j in self.sections() if j[:5]=='Setup' and ':Guide' in j]
    
    def setup_subsections(self):
        """Return setup subsection names"""
        return [j for j in self.sections() if j[:5]=='Setup' and ':' in j]
    
    def file_version(self):
        return self.get('Plate','formatversion')
    
    def get_targets(self, setup_section):
        """Return list of target dictionaries for setup section"""
        return self._extract_list_to_dictlist(setup_section+':Targets',
                                              keep_key_as='fiber')

    def _extract_list_to_dictlist(self,section, keep_key_as=None):
        """ get list of dicts with keys based on header row"""
        hrec=self.get(section,'H')
        recs=filter(lambda x: x[0]!='h', self.items(section))
        if not recs:
            return []
        if '\t' in hrec:
            tabquote=True
            keys=map(str.lower, _extract_tab_quote_list(hrec))
        else:
            tabquote=False
            keys=map(str.lower, hrec.split())
    
        if tabquote:
            extr_func=_extract_tab_quote_list
        else:
            extr_func=str.split

        if recs[0][0][0]=='t':
            keep_key_as=None  #TODO remove hack for v.1 fiber section with not needed

        ret=[]
        for k, rec in recs:
            vals=extr_func(rec)
            rdict={keys[i].lower():vals[i] for i in range(len(keys))}# if vals[i] !='-'}
            if keep_key_as:
                rdict[keep_key_as]=k.upper()
            ret.append(rdict)
        return ret

    def get_guides(self, setup_section):
        """Return list of target dictionaries for setup section"""
        if not self.has_section(setup_section+':Guide'):
            return []
        return self._extract_list_to_dictlist(setup_section+':Guide')
        
    def get_unused(self, setup_section):
        """Return list of target dictionaries for setup section"""
        if not self.has_section(setup_section+':Unused'):
            return []
        return self._extract_list_to_dictlist(setup_section+':Unused')

    def get_plate_holes(self):
        if not self.has_section('PlateHoles'):
            return []
        return self._extract_list_to_dictlist('PlateHoles')

    def setup_attrib(self,setup):
        """Get the setup attribute dict"""
        #Post process (ra,de) and (az,el) keys
        attrib=dict(self.items(setup))
        try:
            azel=attrib.pop('(az,el)').split(',')
            attrib['az']=azel[0].strip('() ')
            attrib['el']=azel[1].strip('() ')
        except KeyError:
            pass
        try:
            rade=attrib.pop('(ra,de)').split(',')
            attrib['ra']=rade[0].strip('() ')
            attrib['de']=rade[1].strip('() ')
        except KeyError:
            pass
        return attrib
    
    def _vet(self):
        """return a list of format errors"""
        
        try:
            version=self.file_version()
        except ConfigParser.NoSectionError:
            return ["Must have [Plate] section."]
        except ConfigParser.NoOptionError:
            return ["[Plate] section must have keyword 'formatversion'."]
        
        errors=[]
        
        #Verify the file has all the required sections
        for section in REQUIRED_SECTIONS[version]:
            if not self.has_section(section):
                errors.append('Required section %s is missing' % section)
        
        #Verify plate section has correct keys
        for key in REQUIRED_PLATE_KEYS[version]:
            if not self.has_option('Plate',key):
                errors.append('Plate section missing key %s' % key)
    
        #Ensure all setup sections have the required subsections & keys
        for setup in self.setup_sections():
            #Subsections
            for subsec in REQUIRED_SETUP_SUBSECTIONS[version]:
                sec=':'.join([setup,subsec])
                if not self.has_section(sec):
                    errors.append(sec+' section is missing')
            #Keys
            for key in REQUIRED_SETUP_KEYS[version]:
                if not self.has_option(setup,key):
                    errors.append(setup+' section missing key '+key)

        #Ensure there is a setup section for every setup subsection
        for subsec in self.setup_subsections():
            setup,_,_=subsec.partition(':')
            if not self.has_section(setup):
                errors.append(setup+' section is missing')

        #Ensure setup names are unique
        setupNames=[]
        for setup in self.setup_sections():
            try:
                name=self.get(setup, 'name')
                if name in setupNames:
                    errors.append("Setup name '%' is not unique" % name)
                    setupNames.append(name)
            except ConfigParser.NoOptionError:
                pass
        
        #At this point we know all the basic data is there
        # The file isn't guarnateed valid yet, as there could still be invalid
        # data for a particular key
        
        #Validate the plate section data
        #TODO

        #Validate the setup sections data
        #TODO

        return errors



    def write(self, file=None):
        if file:
            self.filename=file
        #get list of crap for the plate
        with open(self.filename,'w') as fp:
        
            for section
                section_name=
                #Write the section
                fp.write("[{}]\n".format(section_name))
                
                section_dict=
                for r in _format_attrib_nicely(section_dict):
                    fp.write(r)

                #Write out mechanical holes
                recs=_dictlist_to_records(self.get_plate_holes(),
                                          PLATEHOLE_REQUIRED_COLS,
                                          PLATEHOLE_KEY)
                for subsection in section:
                    subsection_name=
                    fp.write("[{}:{}]\n".format(section_name, subsection_name))
        
                    section_records=
                    recs=_dictlist_to_records(self.get_plate_holes(),
                                              REQUIRED_COLS[section],
                                              PLATEHOLE_KEY)
        
                    #Write out the Guide section
                    recs=_dictlist_to_records(self.get_guides(s),
                                              GUIDE_REQUIRED_COLS,
                                              GUIDE_KEY)
                        
                    for r in recs:
                        fp.write(r)



    def read(self, filename):

        basename=os.path.basename(filename)
        

        try:
            lines=open(file,'r').readlines()
        except IOError as e:
            raise e

        lines=[l.strip() for l in lines]
        """
        
        sections={}
        may contain any combination of
        key:str_val pairs
        section_name:list_of_dicts pairs
        section_name:section_dict pairs
        
        section_dicts may contain any combination of
        key:str_val pairs
        subsection_name:list_of_dicts pairs
        section_name:subsection_dict pairs
        
        k=val pairs must all come prior to any records
        
        record headings are only allowed once and must be first line after
        k=val pairs
        
        """
        try:
            for i,l in (i,l for i,l in enumerate(lines) if l):
                if l[0] =='#':
                    continue
                elif l[0] == '[':
                    if l[-1]!=']' or ' ' in l:
                        raise Exception('Formatting Error line {}: {}'.format(i,l))
                    
                    #New section or subsection
                    
                    #Close out loading of records if needed
                    if records:
                        add_to_sections(sec_name, subsec_name, recs=records)

                    sec_name=None
                    subsec_name=None
                    columns=None
                    records=[]
                    if ':' in l:
                        section_name,subsection_name=l[1:-1].split(':')
                        sections[section_name]={}
                    else:
                        section_name=l[1:-1]
                        subsection_name=None
                    section_start=True
                    continue
                else:
                    if not columns:
                        if '=' in l:
                            key,val=map(lambda x: x.strip(), l.split('='))
                            if ' ' in key or ' ' in val:
                                raise Exception('Formatting Error line {}: {}'.format(i,l))
                            add_to_sections(sec_name, subsec_name, key, val)
                        else:
                            columns=_parse_header_row(l.lower())
                    else:
                        records.append(_parse_record_row(l, columns))
def add_to_sections(sections, sec_name, subsec_name, key=None, val=None, recs=None):

    if recs and not sec_name:
        raise ValueError('Dictlist must go into a section')
    if not recs:
        key, val = args
    if not sec_name:
        sections[key]=val
    if not
    
                        k,_,v=l.partition('=')
                        k=k.strip().lower()
                        if k=='field':
                            k='name'
                        v=v.strip()
                        assert v != ''
                    except Exception as e:
                        raise Exception('Bad key=value formatting: {}'.format(str(e)))
                    if k in VALID_TYPE_CODES:
                        raise Exception('Key {} not allowed.'.format(k))
                    if k in PROGRAM_KEYS and ret[k]==None:
                        if k=='obsdate':
                            ret[k]=datetime(*map(int, v.split()))
                        else:
                            ret[k]=v
                    elif k not in ret['user']:
                        ret['user'][k]=v
                    else:
                        raise Exception('Key {} may only be defined once.'.format(k))
                elif l.lower().startswith('ra'):
                    keys=_parse_header_row(l.lower())
                else:
                    hole=Hole()
                    hole.update(_parse_record_row(l, keys))
                    ret[hole['type']].append(hole)
        except Exception as e:
            raise IOError('Failed on line '
                            '{}: {}\n  Error:{}'.format(lines.index(l),l,str(e)))
        #Use the s-h (or field center id if none) as the field name if one wasn't
        # defined
        if not ret['name']:
            ret['name']=ret['C'][0]['id']

        for t in ret['C']:
            t['x'],t['y'],t['z'],t['r']=0.0,0.0,0.0,SH_RADIUS

        return ret

