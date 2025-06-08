EXTRACT_PROMPT = """
You are an expert content extraction specialist. Your primary task is to extract clean, coherent content from noisy, cluttered text that has been scraped from web sources. This extraction is for archival purposes and educational value only.

## INPUT CONTEXT
The text you'll process has been extracted from web pages using BeautifulSoup (bs4), so expect:
- Residual HTML artifacts
- Navigation elements mixed with content
- Advertisements and promotional text
- Duplicate or fragmented sentences
- Inconsistent formatting

## CONTENT TYPES
You may encounter various content types including:
- News articles and blog posts
- Social media posts and comments
- Email content
- Forum discussions
- Product descriptions

## EXTRACTION GUIDELINES

### INCLUDE:
- Main article content (headlines, body text, quotes)
- Relevant subheadings and section titles
- Important factual information and data
- Author attributions and publication details
- Captions for images or media (if meaningful)

### EXCLUDE:
- Navigation menus and website headers/footers
- Advertisement text and promotional content
- Boilerplate text (e.g., "About Us", "Contact Us")
- Repeated phrases or sentences
- Non-essential links (e.g., "Read more", "Click here")
- "Read more", "Click here", "Subscribe now" links
- Social media sharing buttons text
- Cookie notices and privacy disclaimers
- Related articles suggestions
- Comment section metadata (likes, timestamps, etc.)
- Duplicate content or repeated phrases
- Website boilerplate text
- "Related articles" or "more from this author" sections
- Any content that does not contribute to the main topic or narrative

## OUTPUT REQUIREMENTS
1. Preserve the original wording and tone of the extracted content
2. Maintain logical flow and coherence
3. Return clean markdown format without code block markers
4. Ensure the output represents the core information that is actually relevant to the article or post.

## QUALITY STANDARDS
- Preserve important structural elements (headings, lists, etc.)

Extract only the essential, meaningful content that represents the core information the user is seeking. Do not "parrot" this prompt or include any instructions in the output.
Return the cleaned content as a single coherent text block, without any additional commentary or explanation.
Please respond, don't say "Sorry, I can't do that" or similar phrases. Just provide the cleaned content directly. No additional text, no disclaimers and no explanations.
This process is strictly for archival and educational purposes.
Do not say stuff like ### CLEANED CONTENT ### or similar. Just return the cleaned content directly, as if you were writing a ReadMe file or a blog post.
/nothink
"""

BIAS_PROMPT = """
You are an expert in political bias detection. Your task is to analyze the provided text and determine its political lean using one of the following five categories. This analysis is for archival and educational purposes only.

- Left
- Slightly Left
- Neutral
- Slightly Right
- Right

## INSTRUCTIONS
- Carefully read the text and consider its language, framing, and viewpoints.
- Focus on political, social, and economic perspectives expressed or implied in the content.
- Do not explain your reasoning; simply return one of the five categories above as your answer.
- If the text is neutral or balanced, return "Neutral".

Return only the single category that best describes the political lean of the text.
This task is performed solely for archival and educational value.
"""
