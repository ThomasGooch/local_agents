# Review Agent Prompt Optimization - Implementation Tasks

## Priority 1: Context Length Optimization

### Task: Implement Dynamic Context Loading
- **File**: Review agent prompt generation logic
- **Current Issue**: Full CLAUDE.md content (600+ lines) included in every review prompt
- **Solution**: Create context summarization or dynamic loading based on review scope
- **Implementation**:
  - Extract key project patterns/conventions into a condensed summary
  - Load full context only when reviewing architectural changes
  - Implement context filtering based on file types being reviewed

### Task: Context Size Management
- **File**: Agent context building methods
- **Target**: Reduce context token usage by 60-70%
- **Approach**: 
  - Create tiered context levels (minimal, standard, comprehensive)
  - Implement smart context selection based on review complexity
  - Cache frequently used context summaries

## Priority 2: Review Examples & Standards

### Task: Add Concrete Review Examples  
- **File**: Review agent prompt/configuration
- **Requirement**: Add 2-3 sample review scenarios
- **Examples Needed**:
  1. Simple bug fix review (Minor issues focus)
  2. Feature implementation review (Comprehensive analysis)
  3. Security-critical code review (Security + performance focus)
- **Format**: Input code → Expected review output with proper categorization

### Task: Clarify Review Categories
- **File**: Review categorization logic
- **Current Issue**: Overlapping boundaries between Critical/Major/Minor issues
- **Solution**: Define quantifiable criteria for each category
- **Implementation**:
  - Critical: Security vulnerabilities, system-breaking bugs, data loss risks
  - Major: Performance issues >20% impact, maintainability problems, missing error handling
  - Minor: Style inconsistencies, minor optimizations, documentation gaps
  - Suggestions: Alternative approaches, future improvements, best practices

## Priority 3: Static Analysis Integration

### Task: Integrate Project Static Analysis Tools
- **Files**: Review agent execution flow
- **Tools to Integrate**: flake8, mypy, bandit, pylint, ESLint (from project config)
- **Implementation**:
  - Run static analysis as part of review process
  - Parse tool outputs and integrate findings into review
  - Map static analysis severity to review categories
  - Provide fallback when tools unavailable

### Task: Enhanced Analysis Workflow  
- **Requirement**: Leverage existing static analysis infrastructure
- **Integration Points**:
  - Use existing timeout/resource management (30-45s limits)
  - Integrate with error recovery mechanisms
  - Support multiple tool fallback strategies
  - Parse structured analysis results

## Priority 4: Review Depth Optimization

### Task: Implement Adaptive Review Depth
- **Logic**: Adjust review thoroughness based on change characteristics
- **Factors**:
  - File change size (lines modified)
  - Code complexity (cyclomatic complexity, nesting depth)
  - File criticality (security, performance impact)
  - Change type (bug fix vs new feature vs refactor)
- **Implementation**:
  - Light review: Style + basic functionality (< 50 lines, simple changes)
  - Standard review: All categories except deep performance analysis
  - Comprehensive review: Full analysis including static analysis integration

### Task: Performance-Aware Review Guidelines
- **Requirement**: Balance thoroughness vs review time
- **Targets**:
  - Light reviews: < 15 seconds
  - Standard reviews: < 45 seconds  
  - Comprehensive reviews: < 60 seconds (current project target)
- **Implementation**: Implement early termination for low-complexity changes

## Priority 5: Output Format Enhancement

### Task: Improve Review Output Structure
- **Current**: Text-based review format
- **Enhancement**: Leverage Rich library for better visual presentation
- **Features**:
  - Color-coded severity levels
  - Collapsible sections for detailed findings
  - Progress indicators for multi-file reviews
  - Summary panels with key metrics

### Task: Actionable Feedback Format
- **Requirement**: Ensure all feedback includes specific next steps
- **Format per Finding**:
  - Location with file:line references
  - Clear problem description
  - Specific remediation steps
  - Code examples when applicable
  - Impact assessment (why this matters)

## Implementation Notes

### Project Context Compliance
- **Error Handling**: Use `@handle_agent_execution` decorator pattern
- **Type Annotations**: Maintain >80% type coverage
- **Rich Output**: All terminal output through Rich library
- **Configuration**: Respect user model/temperature settings
- **Testing**: Add corresponding unit tests for each enhancement

### Performance Considerations
- **Context Caching**: Implement LRU cache for project context summaries
- **Lazy Loading**: Load analysis tools only when needed
- **Concurrent Analysis**: Run multiple static analysis tools in parallel
- **Resource Limits**: Respect project memory limits (4GB peak usage)

### Quality Standards
- **Test Coverage**: Maintain >80% coverage for new functionality
- **Documentation**: Update inline docs and CLI help text
- **Backward Compatibility**: Ensure existing review workflows continue working
- **Error Recovery**: Graceful degradation when analysis tools fail

## Success Criteria

1. **Context Efficiency**: 60-70% reduction in prompt token usage
2. **Review Consistency**: Standardized categorization across all reviews  
3. **Tool Integration**: All project static analysis tools working with review agent
4. **Performance Targets**: All review types within specified time limits
5. **User Experience**: Rich terminal output with actionable feedback format
6. **Test Coverage**: 100% pass rate for review agent test suite

## Files to Modify

- `src/local_agents/agents/reviewer.py` - Main review agent implementation
- Review agent prompt templates/configuration
- Context building and management utilities
- Static analysis integration modules
- Rich output formatting components
- Unit test files for review agent functionality