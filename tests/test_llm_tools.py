#!/usr/bin/env python3
"""
Test script to evaluate Qwen-3-4B's function calling capabilities with Ollama.
This tests if the model can extract structured note metadata reliably.
"""

import json
import ollama
from typing import Dict, Any

# Define our note organization tool
NOTE_ORGANIZER_TOOL = {
    'type': 'function',
    'function': {
        'name': 'organize_note',
        'description': 'Organize a note with title, folder, and tags',
        'parameters': {
            'type': 'object',
            'properties': {
                'title': {
                    'type': 'string',
                    'description': 'A concise title for the note (max 10 words)',
                },
                'folder': {
                    'type': 'string',
                    'description': 'The folder to save the note in',
                    'enum': ['inbox', 'projects', 'people', 'research', 'journal']
                },
                'tags': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Relevant tags for the note (3-6 tags, lowercase with underscores)',
                },
                'first_sentence': {
                    'type': 'string',
                    'description': 'The first sentence or key point of the note',
                }
            },
            'required': ['title', 'folder', 'tags', 'first_sentence'],
        },
    },
}

# Test cases with expected outputs
TEST_CASES = [
    {
        'input': "Consider ALB public, Fargate private. Check ECR VPC endpoints issue. Need to review AWS networking setup for the new deployment.",
        'expected': {
            'folder': 'projects',
            'tags_should_include': ['aws', 'networking'],
        }
    },
    {
        'input': "Met with Sarah from the design team about the new dashboard. She suggested using a card-based layout with real-time updates. Follow up next week.",
        'expected': {
            'folder': 'people',
            'tags_should_include': ['design', 'meeting'],
        }
    },
    {
        'input': "Discovered that React 18's automatic batching significantly reduces re-renders. This could solve our performance issues in the data grid component.",
        'expected': {
            'folder': 'research',
            'tags_should_include': ['react', 'performance'],
        }
    },
    {
        'input': "Feeling productive today. Finished three major tasks and cleaned up the codebase. Tomorrow focus on the API integration.",
        'expected': {
            'folder': 'journal',
            'tags_should_include': ['productivity'],
        }
    },
    {
        'input': "Buy milk and eggs. Call dentist. Review pull requests.",
        'expected': {
            'folder': 'inbox',
            'tags_should_include': ['todo'],
        }
    },
]

def test_tool_calling(model_name: str = 'qwen3:4b-instruct') -> Dict[str, Any]:
    """Test if the model supports tool calling."""
    print(f"\n{'='*60}")
    print(f"Testing tool calling with model: {model_name}")
    print(f"{'='*60}\n")

    results = {
        'model': model_name,
        'supports_tools': False,
        'test_results': [],
        'summary': {}
    }

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"Test Case {i}:")
        print(f"Input: {test_case['input'][:80]}...")

        try:
            # Try with tool calling
            response = ollama.chat(
                model=model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a note organization assistant. Analyze the given text and organize it appropriately.'
                    },
                    {
                        'role': 'user',
                        'content': f"Please organize this note: {test_case['input']}"
                    }
                ],
                tools=[NOTE_ORGANIZER_TOOL]
            )

            # Check if tool_calls exist
            message = response.get('message', {})

            # Handle both dict and object responses
            if hasattr(message, 'tool_calls'):
                tool_calls = message.tool_calls
            else:
                tool_calls = message.get('tool_calls')

            if tool_calls:
                results['supports_tools'] = True

                # Convert tool_calls to serializable format if needed
                if hasattr(tool_calls[0], '__dict__'):
                    # It's an object, extract the attributes
                    tool_call = tool_calls[0]
                    if hasattr(tool_call, 'function'):
                        func = tool_call.function
                        args = func.arguments if hasattr(func, 'arguments') else func.get('arguments', {})
                        if isinstance(args, str):
                            args = json.loads(args)

                        print(f"✅ Tool call received")
                        print(f"  Function: {func.name if hasattr(func, 'name') else func.get('name')}")
                        print(f"  Arguments: {json.dumps(args, indent=2)}")

                        # Check against expected
                        folder_match = args.get('folder') == test_case['expected']['folder']
                        tags = args.get('tags', [])
                        tags_match = any(tag in tags for tag in test_case['expected']['tags_should_include'])

                        result = {
                            'success': folder_match and tags_match,
                            'folder_correct': folder_match,
                            'tags_correct': tags_match,
                            'extracted': args
                        }
                        results['test_results'].append(result)
                        print(f"  Folder: {args.get('folder')} {'✓' if folder_match else '✗'}")
                        print(f"  Tags: {args.get('tags')} {'✓' if tags_match else '✗'}")
                else:
                    # It's already a dict
                    print(f"✅ Tool calls received: {json.dumps(tool_calls, indent=2)}")
                    call = tool_calls[0]
                    if 'function' in call:
                        args = call['function'].get('arguments', {})
                        if isinstance(args, str):
                            args = json.loads(args)

                        # Check against expected
                        folder_match = args.get('folder') == test_case['expected']['folder']
                        tags = args.get('tags', [])
                        tags_match = any(tag in tags for tag in test_case['expected']['tags_should_include'])

                        result = {
                            'success': folder_match and tags_match,
                            'folder_correct': folder_match,
                            'tags_correct': tags_match,
                            'extracted': args
                        }
                        results['test_results'].append(result)
                        print(f"  Folder: {args.get('folder')} {'✓' if folder_match else '✗'}")
                        print(f"  Tags: {args.get('tags')} {'✓' if tags_match else '✗'}")
            else:
                print("⚠️  No tool_calls in response")
                # Try to print just the content
                if hasattr(message, 'content'):
                    print(f"Response content: {message.content[:200]}...")
                else:
                    print(f"Response type: {type(message)}")
                results['test_results'].append({'success': False, 'error': 'No tool calls'})

        except Exception as e:
            print(f"❌ Error: {e}")
            results['test_results'].append({'success': False, 'error': str(e)})

        print()

    # Calculate summary
    if results['test_results']:
        successful = sum(1 for r in results['test_results'] if r.get('success', False))
        results['summary'] = {
            'total_tests': len(TEST_CASES),
            'successful': successful,
            'success_rate': f"{(successful/len(TEST_CASES))*100:.1f}%"
        }

    return results

def test_json_extraction(model_name: str = 'qwen3:4b-instruct') -> Dict[str, Any]:
    """Fallback test: Can the model output structured JSON without tools?"""
    print(f"\n{'='*60}")
    print(f"Testing JSON extraction (fallback) with model: {model_name}")
    print(f"{'='*60}\n")

    results = {
        'model': model_name,
        'test_results': [],
        'summary': {}
    }

    system_prompt = """You are a note organizer. Output ONLY valid JSON with this exact structure:
{"title":"...","folder":"inbox|projects|people|research|journal","tags":["..."],"first_sentence":"..."}
- Title: max 10 words
- Folder: choose the most appropriate
- Tags: 3-6 relevant tags, lowercase with underscores
- First_sentence: extract the main point
NO other text, ONLY the JSON object."""

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"Test Case {i}:")
        print(f"Input: {test_case['input'][:80]}...")

        try:
            response = ollama.chat(
                model=model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': test_case['input']}
                ],
                options={'temperature': 0.1}  # Lower temperature for consistency
            )

            content = response['message']['content'].strip()
            print(f"Raw response: {content[:200]}...")

            # Try to parse JSON
            try:
                # Find JSON in response
                start = content.find('{')
                end = content.rfind('}')
                if start >= 0 and end > start:
                    json_str = content[start:end+1]
                    data = json.loads(json_str)

                    # Validate
                    folder_match = data.get('folder') == test_case['expected']['folder']
                    tags = data.get('tags', [])
                    tags_match = any(tag in tags for tag in test_case['expected']['tags_should_include'])

                    result = {
                        'success': True,
                        'folder_correct': folder_match,
                        'tags_correct': tags_match,
                        'extracted': data
                    }
                    results['test_results'].append(result)

                    print(f"✅ JSON parsed successfully")
                    print(f"  Title: {data.get('title')}")
                    print(f"  Folder: {data.get('folder')} {'✓' if folder_match else '✗'}")
                    print(f"  Tags: {data.get('tags')} {'✓' if tags_match else '✗'}")
                else:
                    print("❌ No JSON found in response")
                    results['test_results'].append({'success': False, 'error': 'No JSON found'})

            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                results['test_results'].append({'success': False, 'error': f'JSON parse error: {e}'})

        except Exception as e:
            print(f"❌ Error: {e}")
            results['test_results'].append({'success': False, 'error': str(e)})

        print()

    # Calculate summary
    if results['test_results']:
        successful = sum(1 for r in results['test_results'] if r.get('success', False))
        results['summary'] = {
            'total_tests': len(TEST_CASES),
            'successful': successful,
            'success_rate': f"{(successful/len(TEST_CASES))*100:.1f}%"
        }

    return results

def main():
    """Run all tests and provide recommendations."""
    print("\n" + "="*60)
    print("QuickNote AI - LLM Capability Test")
    print("="*60)

    # List available models
    try:
        models = ollama.list()
        print("\nAvailable models:")
        for model in models['models']:
            print(f"  - {model['name']} ({model['size'] / 1e9:.1f}GB)")
    except Exception as e:
        print(f"Could not list models: {e}")

    # Test with Qwen models
    test_models = [
        'qwen3:4b-instruct',  # The model from test_ollama.py
    ]

    all_results = []

    for model in test_models:
        try:
            # Check if model exists
            ollama.show(model)

            # Test tool calling
            tool_results = test_tool_calling(model)
            all_results.append(('tool_calling', tool_results))

            # Test JSON extraction as fallback
            json_results = test_json_extraction(model)
            all_results.append(('json_extraction', json_results))

        except ollama.ResponseError as e:
            if 'not found' in str(e).lower():
                print(f"\n⚠️  Model {model} not found. Skipping...")
                print(f"   Install with: ollama pull {model}")
            else:
                print(f"\n❌ Error testing {model}: {e}")

    # Provide recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)

    best_method = None
    best_model = None
    best_score = 0

    for method, results in all_results:
        if results.get('summary', {}).get('successful', 0) > best_score:
            best_score = results['summary']['successful']
            best_method = method
            best_model = results['model']

    if best_score > 0:
        print(f"\n✅ Best configuration:")
        print(f"   Model: {best_model}")
        print(f"   Method: {'Tool Calling' if best_method == 'tool_calling' else 'JSON Extraction'}")
        print(f"   Success rate: {(best_score/len(TEST_CASES))*100:.1f}%")

        if best_method == 'json_extraction':
            print(f"\n📝 Note: This model doesn't support native tool calling.")
            print(f"   The JSON extraction method will be used as fallback.")
    else:
        print("\n⚠️  No successful configurations found.")
        print("   Consider using a larger model or implementing a more robust fallback.")

    print("\n💡 For production, consider:")
    print("   1. Adding retry logic with different prompts")
    print("   2. Implementing a confidence threshold")
    print("   3. Having human-in-the-loop for low confidence cases")
    print("   4. Using embeddings for folder/tag suggestions")

if __name__ == "__main__":
    main()