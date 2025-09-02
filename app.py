import os
import json
import logging
from flask import Flask, render_template, request, jsonify, send_file, make_response
from flask import Flask, request, jsonify, send_from_directory
import requests
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fastgenius-secret-key")

# Together API configuration
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY", "21c340b3fdc58cf97d62c7c111a4b599c0824e335b5f7a9268460581cb719ba1")
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"

# Content generation templates
TEMPLATES = {
    "quickwriter": {
        "name": "QuickWriter",
        "description": "Generate articles, blog posts, product descriptions, or essays",
        "prompt": """You are FastGenius, an expert content writer.

Task: Write a {content_type} about {topic}
Tone: {tone}
Length: {length}
Language: {language}

Generate well-written, engaging content that matches the specified tone and length.

Return only JSON like:
{{
  "title": "...",
  "content": "..."
}}"""
    },
    "instant_replies": {
        "name": "Instant Replies",
        "description": "Generate email/chat replies based on message tone",
        "prompt": """You are FastGenius, an expert communication assistant.

Task: Generate a reply to this message: {topic}
Tone: {tone}
Length: {length}
Language: {language}

Generate an appropriate reply that matches the specified tone and length.

Return only JSON like:
{{
  "title": "Reply",
  "content": "..."
}}"""
    },
    "resume_bio": {
        "name": "Resume/Job Bio Generator",
        "description": "Generate personal bio or resume intro for job roles",
        "prompt": """You are FastGenius, an expert career counselor.

Task: Generate a professional bio/resume intro for {topic}
Tone: {tone}
Length: {length}
Language: {language}

Generate a compelling professional bio that highlights relevant skills and experience.

Return only JSON like:
{{
  "title": "Professional Bio",
  "content": "..."
}}"""
    },
    "eli5": {
        "name": "Explain Like I'm 5",
        "description": "Explain any topic in a super simple way",
        "prompt": """You are FastGenius, an expert educator who explains things simply.

Task: Explain {topic} in a very simple way that a 5-year-old could understand
Tone: {tone}
Length: {length}
Language: {language}

Use simple words, analogies, and examples. Make it fun and easy to understand.

Return only JSON like:
{{
  "title": "Simple Explanation",
  "content": "..."
}}"""
    },
    "homework_helper": {
        "name": "Homework Helper",
        "description": "Get clean, short educational answers",
        "prompt": """You are FastGenius, an expert tutor.

Task: Help answer this homework question: {topic}
Tone: {tone}
Length: {length}
Language: {language}

Provide a clear, educational answer that helps the student understand the concept.

Return only JSON like:
{{
  "title": "Answer",
  "content": "..."
}}"""
    },
    "startup_pitch": {
        "name": "Startup Pitch",
        "description": "Transform your idea into a 3-line elevator pitch",
        "prompt": """You are FastGenius, an expert startup advisor.

Task: Create a 3-line elevator pitch for this idea: {topic}
Tone: {tone}
Length: {length}
Language: {language}

Generate a compelling, concise elevator pitch that captures the essence of the idea.

Return only JSON like:
{{
  "title": "Elevator Pitch",
  "content": "..."
}}"""
    },
    "custom_prompt": {
        "name": "Custom Prompt Builder",
        "description": "Create your own prompt templates",
        "prompt": """You are FastGenius, an expert assistant.

Task: {topic}
Tone: {tone}
Length: {length}
Language: {language}

Generate a well-written output based on the custom request.

Return only JSON like:
{{
  "title": "Custom Output",
  "content": "..."
}}"""
    }
}

def generate_content_with_together(prompt):
    """Generate content using Together API"""
    try:
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "messages": [
                {
                    "role": "system",
                    "content": "You are FastGenius, an AI assistant that generates high-quality content quickly. Always respond with valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        
        response = requests.post(TOGETHER_API_URL, json=data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Try to parse JSON from the response
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                return json.loads(json_content)
            else:
                # Fallback if JSON parsing fails
                return {
                    "title": "Generated Content",
                    "content": content
                }
        except json.JSONDecodeError:
            return {
                "title": "Generated Content",
                "content": content
            }
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Together API request failed: {e}")
        return {
            "title": "Error",
            "content": "Sorry, there was an error generating content. Please try again."
        }
    except Exception as e:
        logging.error(f"Content generation failed: {e}")
        return {
            "title": "Error",
            "content": "Sorry, there was an unexpected error. Please try again."
        }

@app.route('/')
def serve_ui():
    return send_from_directory('templates', 'index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Generate content based on user input"""
    try:
        data = request.get_json()
        
        template_id = data.get('template', 'quickwriter')
        topic = data.get('topic', '')
        tone = data.get('tone', 'professional')
        length = data.get('length', 'medium')
        language = data.get('language', 'english')
        content_type = data.get('content_type', 'article')
        
        if not topic:
            return jsonify({
                "success": False,
                "error": "Topic is required"
            }), 400
        
        if template_id not in TEMPLATES:
            return jsonify({
                "success": False,
                "error": "Invalid template"
            }), 400
        
        template = TEMPLATES[template_id]
        prompt = template["prompt"].format(
            topic=topic,
            tone=tone,
            length=length,
            language=language,
            content_type=content_type
        )
        
        result = generate_content_with_together(prompt)
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        logging.error(f"Generation endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": "An error occurred while generating content"
        }), 500

@app.route('/export', methods=['POST'])
def export():
    """Export generated content as text file"""
    try:
        data = request.get_json()
        title = data.get('title', 'Generated Content')
        content = data.get('content', '')
        
        if not content:
            return jsonify({
                "success": False,
                "error": "No content to export"
            }), 400
        
        # Create text file content
        file_content = f"{title}\n{'=' * len(title)}\n\n{content}"
        
        # Create file-like object
        file_obj = BytesIO(file_content.encode('utf-8'))
        
        # Generate filename
        filename = f"{title.replace(' ', '_').lower()}.txt"
        
        return send_file(
            file_obj,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logging.error(f"Export endpoint error: {e}")
        return jsonify({
            "success": False,
            "error": "An error occurred while exporting content"
        }), 500

@app.route('/templates')
def get_templates():
    """Get available templates"""
    return jsonify({
        "templates": {
            key: {
                "name": value["name"],
                "description": value["description"]
            }
            for key, value in TEMPLATES.items()
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
