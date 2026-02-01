import configparser

class Localization:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Localization, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        config = configparser.ConfigParser()
        config.read('config/config.ini')
        self.language = config.get('ARLIAI', 'OUTPUT_LANGUAGE', fallback='English')
        
        lang_lower = self.language.lower()
        if lang_lower in ['german', 'de', 'deutsch']:
            self.lang_key = 'de'
        elif lang_lower in ['spanish', 'es', 'español']:
            self.lang_key = 'es'
        else:
            self.lang_key = 'en'

        self.strings = {
            'en': {
                'today_is': "Today is {date}.",
                'articles_published_on': "These articles were published on {date}.",
                'articles_published_between': "These articles were published between {start_date} and {end_date}.",
                'error_prompt_missing': "Error: Prompt File Missing",
                'error_prompt_error': "Error: Prompt File Error",
                'error_intro_generation': "Thoth was unable to generate an introduction for this post due to an API error after multiple retries.",
                'error_system_prompt': "System Prompt File Error",
                'error_curation_prompt': "Curation Prompt File Error",
                'error_content_empty': "Content Error - Empty Body",
                'error_api_http': "API Error - HTTP {status}",
                'error_api_overloaded': "API Error - Model Overloaded (Max Retries)",
                'error_api_network': "API Error - Network Issue (Max Retries)",
                'error_json': "JSON Error",
                'error_response': "Response Error",
                'error_unexpected': "Unexpected Error",
                'error_max_retries': "API Error - Max Retries Exceeded (General)",
                'ai_curation_by': "AI Curation by [Thoth](https://github.com/remlaps/Thoth)",
                'unlocking_rewards': "Unlocking #lifetime-rewards for Steem's creators and #passive-rewards for delegators",
                'generated_with': "This post was generated with the assistance of the following AI model(s): <i>{model}</i>",
                'image_by_ai': "Image by AI",
                'featured_articles': "Here are the articles that are featured in this curation post:<br><br>",
                'table_tags': "Tags",
                'table_created': "Created",
                'disclaimer_endorsement': "Obviously, inclusion in this list does not imply endorsement of the author's ideas.  The list was built by AI and other automated tools, so the results may contain hallucinations, errors, or controversial opinions.  If you see content that should be filtered in the future, please let the operator know.",
                'disclaimer_voting': "If the highlighted post has already paid out, you can upvote this post in order to send rewards to the included authors.  If it is still eligible for payout, you can also click through and vote on the original post.  Either way, you may also wish to click through and engage with the original author!",
                'about_thoth_title': "### About <b><i>Thoth</i></b>:",
                'about_thoth_desc': "Named after the ancient Egyptian god of writing, science, art, wisdom, judgment, and magic, <b><i>Thoth</i></i> is an Open Source curation bot that is intended to align incentives for authors and investors towards the production and support of creativity that attracts human eyeballs to the Steem blockchain.<br><br>",
                'thoth_goals_intro': "This will be done by:",
                'thoth_goal_1': "1. Identifying attractive posts on the blockchain - past and present;",
                'thoth_goal_2': "2. Highlighting those posts for curators;",
                'thoth_goal_3': "3. Delivering beneficiary rewards to the creators who are producing blockchain content with lasting value; and",
                'thoth_goal_4': "4. Delivering beneficiary rewards to the delegators who support the curation initiative.<br><br>",
                'thoth_note_1': "- No rate of return is guaranteed or implied.",
                'thoth_note_2': "- Reward amounts are entirely determined by blockchain consensus.",
                'thoth_note_3': "- Delegator beneficiaries are randomly selected for inclusion in each post and reply with a weighting based on the amount of Steem Power delegated.",
                'operated_by': "This Thoth instance is operated by {operator}",
                'contribute_link': "You can contribute to Thoth or download your own copy of the code, [here](https://github.com/remlaps/Thoth)",
                'post_title': "Curated by Thoth - {timestamp}",
                'reply_table_ref': "Original Post Reference #",
                'reply_table_title': "Title",
                'reply_table_author': "Author",
                'beneficiaries_title': "Beneficiaries",
                'thoth_operator_title': "Thoth Operator",
                'curated_author_title_singular': "Curated Author",
                'curated_author_title_plural': "Curated Authors",
                'curated_author_gratitude': "Thank you for creating the content that makes Steem a vibrant and interesting place. Your creativity is the foundation of our social ecosystem.",
                'delegator_title_singular': "Delegator",
                'delegator_title_plural': "Delegators",
                'delegator_gratitude': "Delegator support is crucial for the Thoth project's ability to find and reward attractive content. Thank you for investing in the Steem ecosystem and the Thoth project.",
                'burn_account_title': "Burn Account",
            },
            'de': {
                'today_is': "Heute ist {date}.",
                'articles_published_on': "Diese Artikel wurden am {date} veröffentlicht.",
                'articles_published_between': "Diese Artikel wurden zwischen dem {start_date} und dem {end_date} veröffentlicht.",
                'error_prompt_missing': "Fehler: Prompt-Datei fehlt",
                'error_prompt_error': "Fehler: Prompt-Datei fehlerhaft",
                'error_intro_generation': "Thoth konnte aufgrund eines API-Fehlers nach mehreren Versuchen keine Einleitung für diesen Beitrag erstellen.",
                'error_system_prompt': "Fehler in der System-Prompt-Datei",
                'error_curation_prompt': "Fehler in der Kurations-Prompt-Datei",
                'error_content_empty': "Inhaltsfehler – leerer Beitrag",
                'error_api_http': "API-Fehler - HTTP {status}",
                'error_api_overloaded': "API-Fehler – Modell überlastet (maximale Anzahl an Versuchen erreicht)",
                'error_api_network': "API-Fehler – Netzwerkproblem (maximale Anzahl an Versuchen erreicht)",
                'error_json': "JSON-Fehler",
                'error_response': "Antwortfehler",
                'error_unexpected': "Unerwarteter Fehler",
                'error_max_retries': "API-Fehler – maximale Anzahl an Versuchen überschritten (allgemein)",
                'ai_curation_by': "KI-Kuration durch [Thoth](https://github.com/remlaps/Thoth)",
                'unlocking_rewards': "Freischaltung von #lifetime-rewards für Steem-Autorinnen und -Autoren und #passive-rewards für Delegierende",
                'generated_with': "Dieser Beitrag wurde mit Unterstützung der folgenden KI-Modelle erstellt: <i>{model}</i>",
                'image_by_ai': "Bild von KI",
                'featured_articles': "Die folgenden Artikel werden in diesem Kurationsbeitrag vorgestellt:<br><br>",
                'table_tags': "Tags",
                'table_created': "Erstellt",
                'disclaimer_endorsement': "Die Aufnahme in diese Liste bedeutet nicht automatisch eine Billigung der Ideen der Autorinnen und Autoren. Die Liste wurde von KI und anderen automatisierten Tools erstellt, daher können die Ergebnisse Halluzinationen, Fehler oder kontroverse Meinungen enthalten. Wenn Sie Inhalte sehen, die künftig gefiltert werden sollten, informieren Sie bitte den Betreiber.",
                'disclaimer_voting': "Wenn der hervorgehobene Beitrag bereits ausgezahlt wurde, können Sie diesen Beitrag hochvoten, um Belohnungen an die aufgeführten Autorinnen und Autoren zu senden. Ist er noch auszahlungsberechtigt, können Sie auch direkt zum Originalbeitrag wechseln und dort abstimmen. In jedem Fall lohnt es sich, den Originalbeitrag zu besuchen und mit der ursprünglichen Autorin oder dem ursprünglichen Autor zu interagieren!",
                'about_thoth_title': "### Über <b><i>Thoth</i></b>:",
                'about_thoth_desc': "Benannt nach dem altägyptischen Gott des Schreibens, der Wissenschaft, der Kunst, der Weisheit, des Urteils und der Magie ist <b><i>Thoth</i></b> ein Open-Source-Kurationsbot, der Anreize für Autorinnen, Autoren und Investoren schaffen soll, kreative Inhalte zu produzieren und zu unterstützen, die menschliche Aufmerksamkeit auf die Steem-Blockchain lenken.<br><br>",
                'thoth_goals_intro': "Dies geschieht durch:",
                'thoth_goal_1': "1. Attraktive Beiträge auf der Blockchain – in Vergangenheit und Gegenwart – identifizieren;",
                'thoth_goal_2': "2. Diese Beiträge für Kuratorinnen und Kuratoren hervorheben;",
                'thoth_goal_3': "3. Begünstigten-Belohnungen an die Erstellerinnen und Ersteller vergeben, die Blockchain-Inhalte mit bleibendem Wert produzieren; und",
                'thoth_goal_4': "4. Begünstigten-Belohnungen an die Delegierenden bereitstellen, die die Kurationsinitiative unterstützen.<br><br>",
                'thoth_note_1': "- Es wird keine Rendite garantiert oder impliziert.",
                'thoth_note_2': "- Belohnungsbeträge werden vollständig durch den Blockchain-Konsens bestimmt.",
                'thoth_note_3': "- Delegator-Begünstigte werden zufällig für die Aufnahme in jeden Beitrag und jede Antwort ausgewählt, mit einer Gewichtung basierend auf der Menge der delegierten Steem Power.",
                'operated_by': "Diese Thoth-Instanz wird betrieben von {operator}",
                'contribute_link': "Sie können zu Thoth beitragen oder Ihre eigene Kopie des Codes herunterladen, [hier](https://github.com/remlaps/Thoth)",
                'post_title': "Kuratiert von Thoth - {timestamp}",
                'reply_table_ref': "Originalbeitrag Referenz #",
                'reply_table_title': "Titel",
                'reply_table_author': "Autor",
                'beneficiaries_title': "Begünstigte",
                'thoth_operator_title': "Thoth-Betreiber",
                'curated_author_title_singular': "Kuratierter Autor",
                'curated_author_title_plural': "Kuratierte Autoren",
                'curated_author_gratitude': "Danke, dass Sie Inhalte erstellen, die Steem zu einem lebendigen und interessanten Ort machen. Ihre Kreativität ist das Fundament unseres sozialen Ökosystems.",
                'delegator_title_singular': "Delegierende",
                'delegator_title_plural': "Delegierende",
                'delegator_gratitude': "Die Unterstützung durch Delegierende ist entscheidend für die Fähigkeit des Thoth-Projekts, attraktive Inhalte zu finden und zu belohnen. Danke, dass Sie in das Steem-Ökosystem und das Thoth-Projekt investieren.",
                'burn_account_title': "Burn-Konto",
            },
            'es': {
                'today_is': "Hoy es {date}.",
                'articles_published_on': "Estos artículos fueron publicados el {date}.",
                'articles_published_between': "Estos artículos fueron publicados entre el {start_date} y el {end_date}.",
                'error_prompt_missing': "Error: Falta el archivo de prompt",
                'error_prompt_error': "Error: El archivo de prompt es incorrecto",
                'error_intro_generation': "Thoth no pudo generar una introducción para este post debido a un error de API después de varios intentos.",
                'error_system_prompt': "Error en el archivo de prompt del sistema",
                'error_curation_prompt': "Error en el archivo de prompt de curación",
                'error_content_empty': "Error de contenido: cuerpo vacío",
                'error_api_http': "Error de API - HTTP {status}",
                'error_api_overloaded': "Error de API: modelo sobrecargado (se alcanzó el número máximo de intentos)",
                'error_api_network': "Error de API: problema de red (se alcanzó el número máximo de intentos)",
                'error_json': "Error JSON",
                'error_response': "Error de respuesta",
                'error_unexpected': "Error inesperado",
                'error_max_retries': "Error de API: se superó el número máximo de intentos (general)",
                'ai_curation_by': "Curación por IA de [Thoth](https://github.com/remlaps/Thoth)",
                'unlocking_rewards': "Desbloqueamos #lifetime-rewards para las personas que crean en Steem y #passive-rewards para quienes delegan",
                'generated_with': "Este post fue generado con la asistencia de los siguientes modelos de IA: <i>{model}</i>",
                'image_by_ai': "Imagen por IA",
                'featured_articles': "Estos son los artículos destacados en esta publicación de curación:<br><br>",
                'table_tags': "Etiquetas",
                'table_created': "Creado",
                'disclaimer_endorsement': "La inclusión en esta lista no implica necesariamente el respaldo de las ideas de las autoras y los autores. La lista fue generada por IA y otras herramientas automatizadas, por lo que los resultados pueden contener alucinaciones, errores u opiniones controvertidas. Si ve contenido que debería filtrarse en el futuro, informe a la persona operadora del sistema.",
                'disclaimer_voting': "Si la publicación destacada ya ha pagado, puede votar esta publicación para enviar recompensas a las autoras y los autores incluidos. Si todavía es elegible para pago, también puede ir a la publicación original y votar allí. En cualquier caso, quizá quiera visitar la publicación original e interactuar con quien la escribió.",
                'about_thoth_title': "### Acerca de <b><i>Thoth</i></b>:",
                'about_thoth_desc': "Llamado así por el antiguo dios egipcio de la escritura, la ciencia, el arte, la sabiduría, el juicio y la magia, <b><i>Thoth</i></b> es un bot de curación de código abierto diseñado para alinear los incentivos de autoras, autores e inversores hacia la producción y el apoyo de creatividad que atrae miradas humanas a la blockchain de Steem.<br><br>",
                'thoth_goals_intro': "Esto se hará mediante:",
                'thoth_goal_1': "1. Identificar publicaciones atractivas en la blockchain, tanto pasadas como presentes;",
                'thoth_goal_2': "2. Destacar esas publicaciones para las personas curadoras;",
                'thoth_goal_3': "3. Entregar recompensas de beneficiarios a las personas creadoras que producen contenido en la blockchain con valor duradero; y",
                'thoth_goal_4': "4. Entregar recompensas de beneficiarios a las personas delegadoras que apoyan la iniciativa de curación.<br><br>",
                'thoth_note_1': "- No se garantiza ni implica ninguna tasa de retorno.",
                'thoth_note_2': "- Los montos de las recompensas son determinados enteramente por el consenso de la blockchain.",
                'thoth_note_3': "- Las personas beneficiarias delegadoras son seleccionadas aleatoriamente para su inclusión en cada post y respuesta con una ponderación basada en la cantidad de Steem Power delegado.",
                'operated_by': "Esta instancia de Thoth es operada por {operator}",
                'contribute_link': "Puede contribuir a Thoth o descargar su propia copia del código, [aquí](https://github.com/remlaps/Thoth)",
                'post_title': "Curado por Thoth - {timestamp}",
                'reply_table_ref': "Referencia de post original #",
                'reply_table_title': "Título",
                'reply_table_author': "Autor",
                'beneficiaries_title': "Beneficiarios",
                'thoth_operator_title': "Operador de Thoth",
                'curated_author_title_singular': "Autor destacado",
                'curated_author_title_plural': "Autores destacados",
                'curated_author_gratitude': "Gracias por crear contenido que hace de Steem un lugar vibrante e interesante. Su creatividad es la base de nuestro ecosistema social.",
                'delegator_title_singular': "Delegante",
                'delegator_title_plural': "Delegantes",
                'delegator_gratitude': "El apoyo de las personas delegantes es crucial para la capacidad del proyecto Thoth de encontrar y recompensar contenido atractivo. Gracias por invertir en el ecosistema Steem y en el proyecto Thoth.",
                'burn_account_title': "Cuenta de quema",
            }
        }
        self._initialized = True

    def get(self, key, **kwargs):
        text = self.strings.get(self.lang_key, {}).get(key, self.strings['en'].get(key, key))
        try:
            if kwargs:
                return text.format(**kwargs)
            return text
        except Exception:
            return text
