from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, FieldList, RadioField, IntegerField, FormField, StringField, TextAreaField
from wtforms.widgets import TextArea
from wtforms.validators import Required, Length

class orgInputForm(Form):
    submit = BooleanField('submit', default = False)
    error_message = TextAreaField('error_message', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])
    jcc_project_id=TextField('pod_name', validators=[Required()])
    user_email=StringField('user_email', validators=[Required()])
    user_firstname=StringField('user_firstname', validators=[Required()])
    user_lastname=StringField('user_lastname', validators=[Required()])
    requestor_email=StringField('requestor_email', validators=[Required()])
    requestor_type=StringField('requestor_type', validators=[Required()])
    environment=StringField('environment', validators=[Required()])
    plex_name=StringField('plex_name', validators=[Required()])
    number_of_cloud=IntegerField('number_of_cloud', validators=[Length(max=2)])
    cloudplex_created=IntegerField('cloudplex_created',validators=[Required()])
    create_sidekick=BooleanField('create_sidekick',validators=[Required()])
    create_cloud=BooleanField('create_cloud',validators=[Required()])
    create_hadooplex=BooleanField('create_hadooplex',validators=[Required()])

class loginForm(Form):
    submit = BooleanField('submit', default = False)
    username=TextField('org_name', validators=[Required()])
    password=TextField('pod_name', validators=[Required()])

class orgPremiumSnapInputForm(Form):
    submit = BooleanField('submit', default = False)
    message_area = TextAreaField('message_area', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])

class orgFeaturesInputForm(Form):
    submit = BooleanField('submit', default = False)
    message_area = TextAreaField('message_area', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])

class groundplexKeysOutputForm(Form):
    submit = BooleanField('submit', default = False)
    message_area = TextAreaField('message_area', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])

class premiumSnapForm(Form):
    select_all = BooleanField('select_all', default = False)
    clear_all = BooleanField('clear_all', default = False)
    message_area = TextAreaField('message_area', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])

class orgFeaturesListForm(Form):
    select_all = BooleanField('select_all', default = False)
    clear_all = BooleanField('clear_all', default = False)
    message_area = TextAreaField('message_area', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])

class dbOutputForm(Form):
    submit = BooleanField('submit', default = False)
    error_message = TextAreaField('error_message', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])

class jccOutputForm(Form):
    submit = BooleanField('submit', default = False)
    record_id=TextField('record_id', validators=[Required()])
    error_message = TextAreaField('error_message', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])

class jccMigrationOutputForm(Form):
    submit = BooleanField('submit', default = False)
    record_id=TextField('record_id', validators=[Required()])
    error_message = TextAreaField('error_message', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])

class SystemControlsForm(Form):
    activate_org_creation = BooleanField('activate_org_creation', default = False)
    activate_jcc_creation = BooleanField('activate_jcc_creation', default = False)
    error_message = TextAreaField('error_message', widget=TextArea())

class orgScriptForm(Form):
    submit = BooleanField('submit', default = False)
    error_message = TextAreaField('error_message', widget=TextArea())
    script_response=TextField('script_response', validators=[Required()])

class jccProjectDisplayForm(Form):
    submit = BooleanField('submit', default = False)
    error_message = TextAreaField('error_message', widget=TextArea())
    script_response=TextField('script_response', validators=[Required()])
    feature_name=TextField('feature_name', validators=[Required()])
    function_type=TextField('function_name', validators=[Required()])
    jcc_project_id=TextField('jcc_project_id', validators=[Required()])

class jccInputForm(Form):
    submit = BooleanField('submit', default = False)
    error_message = TextAreaField('error_message', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])
    mrc=TextField('mrc', validators=[Required()])
    build_prefix=TextField('build_prefix', validators=[Required()])
    deploy_jcc = BooleanField('deploy_jcc', default = True)
    jcc_name=TextField('jcc_name', validators=[Required()])
    instance_id=TextField('jcc_name', validators=[Required()])
    jcc_create_status=TextField('jcc_create_status', validators=[Required()])
    jcc_deploy_status=TextField('jcc_deploy_status', validators=[Required()])
    jcc_create_message_log=TextField('jcc_create_message_log', validators=[Required()])
    jcc_deploy_message_log=TextField('jcc_deploy_message_log', validators=[Required()])

class jccMigrationInputForm(Form):
    submit = BooleanField('submit', default = False)
    error_message = TextAreaField('error_message', widget=TextArea())
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])
    mrc=TextField('mrc', validators=[Required()])
    build_prefix=TextField('build_prefix', validators=[Required()])
    deploy_jcc = BooleanField('deploy_jcc', default = True)
    jcc_name=TextField('jcc_name', validators=[Required()])
    instance_id=TextField('jcc_name', validators=[Required()])
    jcc_create_status=TextField('jcc_create_status', validators=[Required()])
    jcc_deploy_status=TextField('jcc_deploy_status', validators=[Required()])
    jcc_create_message_log=TextField('jcc_create_message_log', validators=[Required()])
    jcc_deploy_message_log=TextField('jcc_deploy_message_log', validators=[Required()])

class dbUpdateOutputForm(Form):
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])
    user_email=StringField('user_email', validators=[Required()])
    org_create_status=StringField('org_create_status', validators=[Required()])
    jcc_create_status=StringField('jcc_create_status', validators=[Required()])
    user_firstname=StringField('user_firstname', validators=[Required()])
    user_lastname=StringField('user_lastname', validators=[Required()])
    requestor_email=StringField('requestor_email', validators=[Required()])
    requestor_type=StringField('requestor_type', validators=[Required()])
    plex_name=StringField('plex_name', validators=[Required()])
    number_of_cloud=IntegerField('number_of_cloud',validators=[Required()])
    cloudplex_created=IntegerField('cloudplex_created',validators=[Required()])
    create_sidekick=BooleanField('create_sidekick',validators=[Required()])
    create_cloud=BooleanField('create_cloud',validators=[Required()])
    create_hadooplex=BooleanField('create_hadooplex',validators=[Required()])
    create_org_flag=BooleanField('create_org_flag',validators=[Required()])
    reate_jcc_flag=BooleanField('create_jcc_flag',validators=[Required()])

class dbSpecialUpdateOutputForm(Form):
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])
    user_email=StringField('user_email', validators=[Required()])
    org_create_status=StringField('org_create_status', validators=[Required()])
    requestor_email=StringField('requestor_email', validators=[Required()])
    requestor_type=StringField('requestor_type', validators=[Required()])
    plex_name=StringField('plex_name', validators=[Required()])
    create_sidekick=BooleanField('create_sidekick',validators=[Required()])
    create_cloud=BooleanField('create_cloud',validators=[Required()])
    create_hadooplex=BooleanField('create_hadooplex',validators=[Required()])
    hadooplex_environment=StringField('hadooplex_environment', validators=[Required()])
    cloudplex_environment=StringField('cloudplex_environment', validators=[Required()])
    groundplex_environment=StringField('groundplex_environment', validators=[Required()])
    hadoop_plex_name=StringField('hadoop_plex_name', validators=[Required()])
    cloud_plex_name=StringField('cloud_plex_name', validators=[Required()])
    ground_plex_name=StringField('ground_plex_name', validators=[Required()])
    
class groundplexDisplayForm(Form):
    org_name=TextField('org_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])

class userVerifyForm(Form):
    user_name=TextField('user_name', validators=[Required()])
    pod_name=TextField('pod_name', validators=[Required()])
    feature_name=TextField('feature_name', validators=[Required()])
    process_type=TextField('process_type', validators=[Required()])
    org_name=TextField('org_name', validators=[Required()])
    group_name=TextField('group_name', validators=[Required()])


