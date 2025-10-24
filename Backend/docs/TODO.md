# TODO: AiMusicSeparator-AI separator backend Improvements

## Recently Completed

### Karaoke Feature (2025-01-14) ✅
- [x] Sync lyrics with timestamps after transcription and separation
- [x] Generate LRC format synchronized lyrics files
- [x] Embed lyrics in audio file metadata (ID3 tags)
- [x] Create dedicated "Karaoke-pjesme" output folder
- [x] Auto-generate karaoke files on upload with auto_process=true
- [x] Add karaoke info to upload API response
- [x] Extend download endpoint to support karaoke files
- [x] Create comprehensive karaoke testing script
- [x] Write detailed /part of AI separator backend/whisperer/WHISPER_KARAOKE_FIX.md documentation

### Previous Improvements ✅
- [x] Auto-process files on upload (Demucs + Gemma 3n)
- [x] 2-stem Demucs separation (vocals + instrumental only)
- [x] Parallel Gemma 3n transcription during upload
- [x] Enhanced processing responses with detailed track info
- [x] Fixed health check notification duplication
- [x] SQL Server 2022 container setup with persistent storage
- [x] Replaced Whisper with Gemma 3n for AI-powered transcription
- [x] Fixed nested Demucs directory structure handling

## Performance and Scaling Improvements
- [ ] Implement model caching to avoid reloading models for each request
- [ ] Add background task queue system (Celery/Redis) for handling long-running model operations asynchronously
- [ ] Implement proper file cleanup scheduling to prevent disk space issues from old uploads/outputs
- [ ] Add connection pooling for database operations if added in the future
- [ ] Implement request throttling/rate limiting to prevent API abuse

## Security Enhancements
- [ ] Add proper authentication system (OAuth2/JWT tokens) for API endpoints
- [ ] Implement more robust validation for file uploads and user inputs
- [ ] Improve CORS policy to be more restrictive in production
- [ ] Add API key validation for sensitive operations
- [ ] Implement input sanitization on text prompts for MusicGen
- [ ] Configure Content Security Policy headers
- [ ] Add security headers (X-Content-Type-Options, X-XSS-Protection, etc.)

## Code Organization and Maintainability
- [ ] Refactor app.py into modular components using Flask Blueprints
- [ ] Create separate route files for each major functionality (audio separation, transcription, music generation)
- [ ] Move WebSocket handlers to a dedicated module
- [ ] Implement proper dependency injection for models and processors
- [ ] Extract common utility functions to a shared module
- [ ] Add more comprehensive docstrings and type hints
- [ ] Create a standardized API response format across all endpoints

## Testing and Quality Assurance
- [ ] Add comprehensive unit tests for all endpoints
- [ ] Implement integration tests for model processors
- [ ] Add API contract tests to validate response formats
- [ ] Set up continuous integration pipeline
- [ ] Add load/stress testing for high traffic scenarios
- [ ] Implement automated security vulnerability scanning

## Error Handling and Monitoring
- [ ] Enhance error messages with more user-friendly details
- [ ] Add centralized error tracking (Sentry.io integration)
- [ ] Implement a more comprehensive logging strategy with structured logs
- [ ] Add metrics collection for model performance and API usage
- [ ] Create a dashboard for monitoring system health

## Feature Enhancements
- [ ] Add batch processing capability for all models
- [ ] Implement progress tracking for long-running operations
- [ ] Add model version tracking for reproducibility
- [ ] Support for more audio formats and conversion options
- [ ] Add caching layer for previously processed files with same parameters
- [ ] Implement webhook notifications for completed processing
- [ ] Add support for custom user-uploaded models

## DevOps and Deployment
- [ ] Containerize models separately for better scaling
- [ ] Add Kubernetes deployment configurations
- [ ] Create separate development/staging/production environments
- [ ] Implement infrastructure-as-code for deployment automation
- [ ] Add automated backup system for processed outputs
- [ ] Improve Docker build process to reduce image size

## Documentation
- [ ] Create comprehensive API documentation with Swagger/OpenAPI
- [ ] Add usage examples for all endpoints
- [ ] Create model-specific processing guides
- [ ] Document environment variables and configuration options
- [ ] Add contribution guidelines and setup instructions

## Lion's Roar Studio Integration
- [ ] Ensure all API endpoints have appropriate CORS headers for frontend consumption
- [ ] Update API contracts to match frontend expectations
- [ ] Add WebSocket event standardization between backend and frontend
- [ ] Implement health check endpoints specifically for frontend monitoring
- [ ] Provide detailed error information that can be presented to users

## Specific Technical Improvements
- [ ] Replace subprocess calls with Python libraries where possible (for Demucs)
- [ ] Optimize memory usage for large file processing
- [ ] Implement streaming responses for large file downloads
- [ ] Add proper database storage instead of relying on filesystem
- [ ] Improve WebSocket connection stability and reconnection handling