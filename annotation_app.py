from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load data
DATA_DIR = '/home/amari810/annotation-tool/data'
ANNOTATIONS_FILE = os.path.join(DATA_DIR, 'annotations.json')

with open(os.path.join(DATA_DIR, 'lesson_index.json'), 'r') as f:
    lesson_index = json.load(f)

with open(os.path.join(DATA_DIR, 'segments_flattened.json'), 'r') as f:
    all_segments = json.load(f)

# Initialize annotations file if it doesn't exist
if not os.path.exists(ANNOTATIONS_FILE):
    with open(ANNOTATIONS_FILE, 'w') as f:
        json.dump({}, f)

def load_annotations():
    """Load existing annotations"""
    with open(ANNOTATIONS_FILE, 'r') as f:
        return json.load(f)

def save_annotations(annotations):
    """Save annotations"""
    with open(ANNOTATIONS_FILE, 'w') as f:
        json.dump(annotations, f, indent=2)

# Routes 
@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/lessons')
def get_lessons():
    """Get list of all lessons"""
    annotations = load_annotations()
    lessons = []
    for lesson_id, lesson_data in lesson_index.items():
        # Count annotated segments in this lesson
        annotated_count = sum(
            1 for seg in lesson_data['segments']
            if f"{lesson_id}_{seg['id']}" in annotations
        )
        lessons.append({
            'id': lesson_id,
            'name': lesson_data['name'],
            'segment_count': lesson_data['segment_count'],
            'annotated_count': annotated_count
        })
    return jsonify(lessons)

@app.route('/api/lesson/<lesson_id>')
def get_lesson_segments(lesson_id):
    """Get all segments for a lesson"""
    if lesson_id not in lesson_index:
        return jsonify({'error': 'Lesson not found'}), 404
    
    segments = lesson_index[lesson_id]['segments']
    annotations = load_annotations()
    
    # Add annotation status to each segment
    for segment in segments:
        segment_key = f"{lesson_id}_{segment['id']}"
        segment['annotation'] = annotations.get(segment_key, None)
        segment['is_annotated'] = segment_key in annotations
    
    return jsonify({
        'lesson_id': lesson_id,
        'lesson_name': lesson_index[lesson_id]['name'],
        'segments': segments
    })

@app.route('/api/annotation/<lesson_id>/<int:segment_id>', methods=['POST'])
def save_annotation(lesson_id, segment_id):
    """Save annotation for a segment"""
    data = request.json
    
    segment_key = f"{lesson_id}_{segment_id}"
    annotations = load_annotations()
    
    annotations[segment_key] = {
        'segment_id': segment_id,
        'lesson_id': lesson_id,
        'category': data.get('category'),
        'subcategory': data.get('subcategory'),
        'reasoning': data.get('reasoning'),
        'confidence': data.get('confidence'),
        'timestamp': datetime.now().isoformat()
    }
    
    save_annotations(annotations)
    return jsonify({'status': 'saved', 'segment_key': segment_key})

@app.route('/api/annotations')
def get_all_annotations():
    """Get all annotations (for export)"""
    return jsonify(load_annotations())

@app.route('/api/export')
def export_annotations():
    """Export annotations with full context"""
    annotations = load_annotations()
    export_data = []
    
    for segment_key, annotation in annotations.items():
        lesson_id, segment_id = segment_key.rsplit('_', 1)
        segment_id = int(segment_id)
        
        # Find original segment
        if lesson_id in lesson_index:
            for seg in lesson_index[lesson_id]['segments']:
                if seg['id'] == segment_id:
                    export_data.append({
                        **annotation,
                        'text': seg['text'],
                        'speaker': seg['speaker'],
                        'start_time': seg['start_time'],
                        'end_time': seg['end_time'],
                        'source_file': seg.get('source_file')
                    })
                    break
    
    return jsonify(export_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
