from flask import Blueprint, render_template

home_bp = Blueprint("home", __name__)

# connects to the index (/) of the web app and shows the homepage, full of useful information
# the 'GET' part tells us what HTTP requests the endpoint can handle (this one just shows data)
@home_bp.route("/", methods=["GET"])
def home():
    # render a html template (webpage); this doesn't refresh the browser window
    return render_template("home.html")


@home_bp.route("/terms", methods=["GET"])
def terms():
    sections = [
        {
            "title": "Using the service",
            "body": [
                "This platform is provided for coursework demonstration, product traceability exploration, and quest gameplay.",
                "You must not upload unlawful, malicious, or misleading content, including false product evidence or abusive issue reports.",
            ],
        },
        {
            "title": "Accounts and roles",
            "body": [
                "Consumers can browse products and play Traceability Quest.",
                "Verifier and admin actions, including adding or editing product data, should only be used by authorised project members.",
            ],
        },
        {
            "title": "Content and availability",
            "body": [
                "Product claims, evidence, and timelines are presented as part of an academic prototype and may not represent a live commercial service.",
                "The service may be changed, reset, or temporarily unavailable during testing and development.",
            ],
        },
    ]
    return render_template(
        "info_page.html",
        page_title="Terms and Conditions",
        page_subtitle="Ground rules for using Single Scan Traceability Quest.",
        sections=sections,
    )


@home_bp.route("/cookies", methods=["GET"])
def cookies():
    sections = [
        {
            "title": "Essential cookies",
            "body": [
                "The site uses essential session cookies to keep users logged in and to maintain secure navigation between pages.",
                "These cookies are required for core features such as authentication, page access control, and flash messages.",
            ],
        },
        {
            "title": "What is not used",
            "body": [
                "This coursework site does not aim to run advertising cookies or third-party tracking cookies as part of the core experience.",
                "If deployment settings change, cookie usage should be reviewed and updated to match the real environment.",
            ],
        },
        {
            "title": "Managing cookies",
            "body": [
                "You can clear or block cookies in your browser settings, but doing so may stop login and other core features from working correctly.",
            ],
        },
    ]
    return render_template(
        "info_page.html",
        page_title="Cookie Information",
        page_subtitle="How cookies are used to support login and core application behaviour.",
        sections=sections,
    )


@home_bp.route("/privacy-security", methods=["GET"])
def privacy_security():
    sections = [
        {
            "title": "Personal data",
            "body": [
                "The application stores account information needed for authentication and user progress, such as usernames, hashed passwords, roles, points, badges, and mission history.",
                "Issue reports and moderation actions may also be linked to user accounts where relevant.",
            ],
        },
        {
            "title": "Security approach",
            "body": [
                "Passwords are stored using hashed values rather than plain text.",
                "Role-based access control is used to limit editing, moderation, and administration features to authorised users.",
            ],
        },
        {
            "title": "Prototype notice",
            "body": [
                "This is a student project prototype, not a production-grade compliance platform.",
                "Sensitive or real-world confidential documents should not be uploaded unless the deployment environment has been explicitly secured for that purpose.",
            ],
        },
    ]
    return render_template(
        "info_page.html",
        page_title="Privacy and Security",
        page_subtitle="What data is stored and how the prototype approaches security.",
        sections=sections,
    )
