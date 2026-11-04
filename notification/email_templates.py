from wagov_utils.components.utils.email import TemplateEmailBase as WAGovUtilsTemplateEmailBase

class AppCheckList(WAGovUtilsTemplateEmailBase):
    """On call IT checks."""
    subject = "On call Applications Team IT Checks"
    html_template = "notification/email/app_check_list.html"
    txt_template = "notification/email/no_txt_support.txt"    