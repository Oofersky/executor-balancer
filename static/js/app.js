/**
 * Executor Balancer Frontend Application
 * Система распределения заявок между исполнителями
 */

class ExecutorBalancerApp {
    constructor() {
        // Use relative URLs to avoid CORS issues
        this.apiBaseUrl = '';
        this.rules = [];
        this.executors = [];
        this.requests = [];
        this.currentSearchResults = [];
        
        this.init();
    }

    init() {
        this.updateTime();
        setInterval(() => this.updateTime(), 1000);
        
        this.loadDashboardData();
        this.loadExecutors();
        this.loadRequests();
        this.loadRules();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            this.loadDashboardData();
            this.loadExecutors();
            this.loadRequests();
        }, 30000);
    }

    updateTime() {
        const now = new Date();
        document.getElementById('current-time').textContent = now.toLocaleString('ru-RU');
    }

    async loadDashboardData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/stats`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            document.getElementById('total-executors').textContent = data.total_executors || 0;
            document.getElementById('active-executors').textContent = data.active_executors || 0;
            document.getElementById('total-requests').textContent = data.total_requests || 0;
            document.getElementById('pending-requests').textContent = data.pending_requests || 0;
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            // Set default values on error
            document.getElementById('total-executors').textContent = '0';
            document.getElementById('active-executors').textContent = '0';
            document.getElementById('total-requests').textContent = '0';
            document.getElementById('pending-requests').textContent = '0';
        }
    }

    async loadExecutors() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/executors`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.executors = data;
            this.renderExecutors();
        } catch (error) {
            console.error('Error loading executors:', error);
            this.executors = [];
            this.renderExecutors();
        }
    }

    async loadRequests() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/requests`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.requests = data;
            this.renderRequests();
        } catch (error) {
            console.error('Error loading requests:', error);
            this.requests = [];
            this.renderRequests();
        }
    }

    async loadRules() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/rules`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.rules = data;
            this.renderRules();
        } catch (error) {
            console.error('Error loading rules:', error);
            this.rules = [];
            this.renderRules();
        }
    }

    renderExecutors() {
        const container = document.getElementById('executors-list');
        if (!container) return;

        if (this.executors.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Исполнители не найдены</div>';
            return;
        }

        container.innerHTML = this.executors.map(executor => `
            <div class="card executor-card mb-3" onclick="app.showExecutorDetails('${executor.id}')">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <h6 class="card-title">${executor.name}</h6>
                            <p class="card-text text-muted">${executor.email}</p>
                            <div class="mb-2">
                                <span class="badge bg-primary">${this.getRoleDisplayName(executor.role)}</span>
                                <span class="badge ${this.getStatusBadgeClass(executor.status)}">${this.getStatusDisplayName(executor.status)}</span>
                                <span class="badge bg-info">Вес: ${executor.weight}</span>
                            </div>
                            <div class="mb-2">
                                <small class="text-muted">
                                    Активных заявок: ${executor.active_requests_count || 0} | 
                                    Успешность: ${(executor.success_rate * 100).toFixed(1)}% | 
                                    Дневной лимит: ${executor.daily_limit || 'Не ограничен'}
                                </small>
                            </div>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="executor-match-score text-success">
                                Рейтинг: ${this.calculateExecutorRating(executor)}
                            </div>
                            <div class="match-reasons">
                                ${this.getExecutorStrengths(executor)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderRequests() {
        const container = document.getElementById('requests-list');
        if (!container) return;

        if (this.requests.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Заявки не найдены</div>';
            return;
        }

        container.innerHTML = this.requests.map(request => `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <h6 class="card-title">${request.title}</h6>
                            <p class="card-text">${request.description}</p>
                            <div class="mb-2">
                                <span class="badge ${this.getPriorityBadgeClass(request.priority)}">${this.getPriorityDisplayName(request.priority)}</span>
                                <span class="badge ${this.getStatusBadgeClass(request.status)}">${this.getStatusDisplayName(request.status)}</span>
                                <span class="badge bg-info">Вес: ${request.weight}</span>
                            </div>
                        </div>
                        <div class="col-md-4 text-end">
                            ${request.assigned_executor_id ? 
                                `<div class="text-success"><i class="fas fa-user-check"></i> Назначен исполнитель</div>` :
                                `<div class="text-warning"><i class="fas fa-clock"></i> Ожидает назначения</div>`
                            }
                            <div class="mt-2">
                                <button class="btn btn-sm btn-outline-primary" onclick="app.searchExecutorsForRequest('${request.id}')">
                                    <i class="fas fa-search"></i> Найти исполнителя
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderRules() {
        const container = document.getElementById('saved-rules');
        if (!container) return;

        if (this.rules.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Правила не найдены</div>';
            return;
        }

        container.innerHTML = this.rules.map(rule => `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <h6 class="card-title">${rule.name}</h6>
                            <p class="card-text">${rule.description}</p>
                            <div class="mb-2">
                                <span class="badge ${this.getPriorityBadgeClass(rule.priority)}">${this.getPriorityDisplayName(rule.priority)}</span>
                                <span class="badge ${rule.is_active ? 'bg-success' : 'bg-secondary'}">${rule.is_active ? 'Активно' : 'Неактивно'}</span>
                            </div>
                            <div class="rule-conditions-preview">
                                ${this.renderRuleConditions(rule.conditions)}
                            </div>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="btn-group-vertical">
                                <button class="btn btn-sm btn-outline-primary" onclick="app.testRule('${rule.id}')">
                                    <i class="fas fa-play"></i> Тестировать
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="app.editRule('${rule.id}')">
                                    <i class="fas fa-edit"></i> Редактировать
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="app.deleteRule('${rule.id}')">
                                    <i class="fas fa-trash"></i> Удалить
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderRuleConditions(conditions) {
        if (!conditions || conditions.length === 0) {
            return '<small class="text-muted">Условия не определены</small>';
        }

        return conditions.map(condition => `
            <div class="parameter-tag">
                ${this.getFieldDisplayName(condition.field)} 
                ${this.getOperatorDisplayName(condition.operator)} 
                ${condition.value}
            </div>
        `).join('');
    }

    async searchExecutors() {
        const loadingSpinner = document.querySelector('.loading-spinner');
        loadingSpinner.classList.add('show');

        try {
            const requestData = this.collectRequestData();
            const response = await fetch(`${this.apiBaseUrl}/search-executors`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const results = await response.json();
            this.currentSearchResults = results;
            this.renderSearchResults(results);
            
            document.getElementById('search-results-card').style.display = 'block';
        } catch (error) {
            console.error('Error searching executors:', error);
            this.showError('Ошибка при поиске исполнителей: ' + error.message);
            document.getElementById('search-results-card').style.display = 'none';
        } finally {
            loadingSpinner.classList.remove('show');
        }
    }

    collectRequestData() {
        const data = {
            title: document.getElementById('request-title').value,
            priority: document.getElementById('request-priority').value,
            weight: parseFloat(document.getElementById('request-weight').value),
            category: document.getElementById('request-category').value,
            complexity: document.getElementById('request-complexity').value,
            estimated_hours: parseInt(document.getElementById('request-estimated-hours').value),
            required_skills: document.getElementById('request-skills').value.split(',').map(s => s.trim()).filter(s => s),
            language_requirement: document.getElementById('request-language').value,
            client_type: document.getElementById('request-client-type').value,
            urgency: document.getElementById('request-urgency').value,
            budget: document.getElementById('request-budget').value ? parseInt(document.getElementById('request-budget').value) : null,
            technology_stack: document.getElementById('request-tech-stack').value.split(',').map(s => s.trim()).filter(s => s),
            timezone_requirement: document.getElementById('request-timezone').value,
            security_clearance: document.getElementById('request-security').value,
            compliance_requirements: document.getElementById('request-compliance').value.split(',').map(s => s.trim()).filter(s => s)
        };
        
        console.log('Collected request data:', data);
        return data;
    }

    renderSearchResults(results) {
        const container = document.getElementById('search-results');
        if (!container) return;

        if (!results || results.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">Подходящие исполнители не найдены</div>';
            return;
        }

        container.innerHTML = results.map((result, index) => `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-8">
                            <h6 class="card-title">
                                ${index + 1}. ${result.executor.name}
                                <span class="badge bg-success ms-2">Совпадение: ${result.match_score.toFixed(1)}%</span>
                            </h6>
                            <p class="card-text text-muted">${result.executor.email}</p>
                            <div class="mb-2">
                                <span class="badge bg-primary">${this.getRoleDisplayName(result.executor.role)}</span>
                                <span class="badge ${this.getStatusBadgeClass(result.executor.status)}">${this.getStatusDisplayName(result.executor.status)}</span>
                                <span class="badge bg-info">Вес: ${result.executor.weight}</span>
                            </div>
                            <div class="mb-2">
                                <small class="text-muted">
                                    Активных заявок: ${result.executor.active_requests_count || 0} | 
                                    Успешность: ${(result.executor.success_rate * 100).toFixed(1)}% | 
                                    Опыт: ${result.executor.experience_years || 0} лет
                                </small>
                            </div>
                            <div class="match-reasons">
                                <strong>Причины выбора:</strong><br>
                                ${result.reasons.map(reason => `• ${reason}`).join('<br>')}
                            </div>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="executor-match-score text-success">
                                Итоговый балл: ${result.final_score.toFixed(2)}
                            </div>
                            <div class="mt-3">
                                <button class="btn btn-success btn-sm" onclick="app.assignExecutor('${result.executor.id}', '${this.getCurrentRequestId()}')">
                                    <i class="fas fa-user-check"></i> Назначить
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async assignExecutor(executorId, requestId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/assign`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    executor_id: executorId,
                    request_id: requestId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.showSuccess('Исполнитель успешно назначен');
            this.loadRequests();
            this.loadDashboardData();
        } catch (error) {
            console.error('Error assigning executor:', error);
            this.showError('Ошибка при назначении исполнителя: ' + error.message);
        }
    }

    async saveRule() {
        const ruleData = this.collectRuleData();
        
        if (!ruleData.name || !ruleData.conditions || ruleData.conditions.length === 0) {
            this.showError('Заполните все обязательные поля');
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/rules`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(ruleData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.showSuccess('Правило успешно сохранено');
            this.loadRules();
            this.clearRuleForm();
        } catch (error) {
            console.error('Error saving rule:', error);
            this.showError('Ошибка при сохранении правила: ' + error.message);
        }
    }

    collectRuleData() {
        const conditions = [];
        const conditionElements = document.querySelectorAll('.rule-condition');
        
        conditionElements.forEach(element => {
            const field = element.querySelector('.field-select').value;
            const operator = element.querySelector('.operator-select').value;
            const value = element.querySelector('.value-input').value;
            
            if (field && operator && value) {
                conditions.push({ field, operator, value });
            }
        });

        return {
            name: document.getElementById('rule-name').value,
            description: document.getElementById('rule-description').value,
            priority: document.getElementById('rule-priority').value,
            conditions: conditions,
            is_active: true
        };
    }

    clearRuleForm() {
        document.getElementById('rule-name').value = '';
        document.getElementById('rule-description').value = '';
        document.getElementById('rule-priority').value = '3';
        
        const conditionsContainer = document.getElementById('rule-conditions');
        conditionsContainer.innerHTML = `
            <div class="rule-condition">
                <div class="row">
                    <div class="col-md-4">
                        <label class="form-label">Поле</label>
                        <select class="form-select field-select" onchange="updateOperators(this)">
                            <option value="">Выберите поле</option>
                            <optgroup label="Исполнитель">
                                <option value="role">Роль</option>
                                <option value="weight">Вес</option>
                                <option value="status">Статус</option>
                                <option value="active_requests_count">Количество активных заявок</option>
                                <option value="success_rate">Процент успешности</option>
                                <option value="daily_limit">Дневной лимит</option>
                                <option value="experience_years">Опыт работы (лет)</option>
                                <option value="specialization">Специализация</option>
                                <option value="language_skills">Языковые навыки</option>
                                <option value="timezone">Часовой пояс</option>
                                <option value="availability_hours">Часы доступности</option>
                                <option value="max_concurrent_tasks">Максимум одновременных задач</option>
                                <option value="response_time_minutes">Время ответа (мин)</option>
                                <option value="quality_rating">Рейтинг качества</option>
                                <option value="certification_level">Уровень сертификации</option>
                                <option value="department">Отдел</option>
                                <option value="manager_id">ID менеджера</option>
                                <option value="cost_per_hour">Стоимость за час</option>
                                <option value="location">Местоположение</option>
                                <option value="remote_work">Удаленная работа</option>
                                <option value="equipment_required">Требуемое оборудование</option>
                            </optgroup>
                            <optgroup label="Заявка">
                                <option value="priority">Приоритет</option>
                                <option value="request_weight">Вес заявки</option>
                                <option value="request_status">Статус заявки</option>
                                <option value="deadline">Дедлайн</option>
                                <option value="category">Категория</option>
                                <option value="complexity">Сложность</option>
                                <option value="estimated_hours">Оценочные часы</option>
                                <option value="client_type">Тип клиента</option>
                                <option value="urgency">Срочность</option>
                                <option value="budget">Бюджет</option>
                                <option value="technology_stack">Технологический стек</option>
                                <option value="required_skills">Требуемые навыки</option>
                                <option value="language_requirement">Требования к языку</option>
                                <option value="timezone_requirement">Требования к часовому поясу</option>
                                <option value="security_clearance">Уровень безопасности</option>
                                <option value="compliance_requirements">Требования соответствия</option>
                            </optgroup>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Оператор</label>
                        <select class="form-select operator-select">
                            <option value="equals">Равно</option>
                            <option value="not_equals">Не равно</option>
                            <option value="greater_than">Больше</option>
                            <option value="less_than">Меньше</option>
                            <option value="greater_than_or_equal">Больше или равно</option>
                            <option value="less_than_or_equal">Меньше или равно</option>
                            <option value="contains">Содержит</option>
                            <option value="in">В списке</option>
                            <option value="not_in">Не в списке</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Значение</label>
                        <input type="text" class="form-control value-input" placeholder="Введите значение">
                    </div>
                    <div class="col-md-1">
                        <label class="form-label">&nbsp;</label>
                        <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeCondition(this)">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        this.updateRulePreview();
    }

    updateRulePreview() {
        const ruleData = this.collectRuleData();
        const previewContainer = document.getElementById('rule-preview');
        const previewContent = document.getElementById('rule-preview-content');
        
        if (ruleData.name && ruleData.conditions && ruleData.conditions.length > 0) {
            previewContainer.style.display = 'block';
            previewContent.innerHTML = `
                <strong>${ruleData.name}</strong><br>
                ${ruleData.description}<br>
                <strong>Условия:</strong><br>
                ${ruleData.conditions.map(condition => 
                    `• ${this.getFieldDisplayName(condition.field)} ${this.getOperatorDisplayName(condition.operator)} ${condition.value}`
                ).join('<br>')}
            `;
        } else {
            previewContainer.style.display = 'none';
        }
    }

    // Utility methods
    getRoleDisplayName(role) {
        const roles = {
            'admin': 'Администратор',
            'programmer': 'Программист',
            'moderator': 'Модератор',
            'support': 'Поддержка',
            'tester': 'Тестировщик',
            'designer': 'Дизайнер',
            'analyst': 'Аналитик',
            'manager': 'Менеджер'
        };
        return roles[role] || role;
    }

    getStatusDisplayName(status) {
        const statuses = {
            'active': 'Активный',
            'inactive': 'Неактивный',
            'busy': 'Занят',
            'pending': 'Ожидает',
            'assigned': 'Назначен',
            'completed': 'Завершен'
        };
        return statuses[status] || status;
    }

    getPriorityDisplayName(priority) {
        const priorities = {
            'critical': 'Критический',
            'high': 'Высокий',
            'medium': 'Средний',
            'low': 'Низкий'
        };
        return priorities[priority] || priority;
    }

    getStatusBadgeClass(status) {
        const classes = {
            'active': 'bg-success',
            'inactive': 'bg-secondary',
            'busy': 'bg-warning',
            'pending': 'bg-warning',
            'assigned': 'bg-info',
            'completed': 'bg-success'
        };
        return classes[status] || 'bg-secondary';
    }

    getPriorityBadgeClass(priority) {
        const classes = {
            'critical': 'bg-danger',
            'high': 'bg-warning',
            'medium': 'bg-primary',
            'low': 'bg-secondary'
        };
        return classes[priority] || 'bg-secondary';
    }

    getFieldDisplayName(field) {
        const fields = {
            'role': 'Роль',
            'weight': 'Вес',
            'status': 'Статус',
            'active_requests_count': 'Активные заявки',
            'success_rate': 'Успешность',
            'daily_limit': 'Дневной лимит',
            'experience_years': 'Опыт работы',
            'specialization': 'Специализация',
            'priority': 'Приоритет',
            'request_weight': 'Вес заявки',
            'category': 'Категория',
            'complexity': 'Сложность'
        };
        return fields[field] || field;
    }

    getOperatorDisplayName(operator) {
        const operators = {
            'equals': 'равно',
            'not_equals': 'не равно',
            'greater_than': 'больше',
            'less_than': 'меньше',
            'greater_than_or_equal': 'больше или равно',
            'less_than_or_equal': 'меньше или равно',
            'contains': 'содержит',
            'in': 'в списке',
            'not_in': 'не в списке'
        };
        return operators[operator] || operator;
    }

    calculateExecutorRating(executor) {
        let rating = 0;
        rating += executor.weight * 40; // Base weight (0-40 points)
        rating += executor.success_rate * 30; // Success rate (0-30 points)
        rating += Math.min(executor.experience_years || 0, 10) * 2; // Experience (0-20 points)
        rating -= executor.active_requests_count * 2; // Load penalty (0-20 points penalty)
        rating = Math.max(0, Math.min(100, rating)); // Clamp between 0-100
        return rating.toFixed(1);
    }

    getExecutorStrengths(executor) {
        const strengths = [];
        if (executor.weight > 0.7) strengths.push('Высокий вес');
        if (executor.success_rate > 0.8) strengths.push('Высокая успешность');
        if ((executor.experience_years || 0) > 5) strengths.push('Опытный');
        if (executor.active_requests_count < 3) strengths.push('Свободен');
        return strengths.join(', ') || 'Стандартные показатели';
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showError(message) {
        this.showAlert(message, 'danger');
    }

    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.parentNode.removeChild(alertDiv);
            }
        }, 5000);
    }

    clearSearch() {
        document.getElementById('request-title').value = '';
        document.getElementById('request-priority').value = 'medium';
        document.getElementById('request-weight').value = '0.5';
        document.getElementById('request-category').value = 'technical';
        document.getElementById('request-complexity').value = 'medium';
        document.getElementById('request-estimated-hours').value = '8';
        document.getElementById('request-skills').value = '';
        document.getElementById('request-language').value = 'ru';
        document.getElementById('request-client-type').value = 'individual';
        document.getElementById('request-urgency').value = 'medium';
        document.getElementById('request-budget').value = '';
        document.getElementById('request-tech-stack').value = '';
        document.getElementById('request-timezone').value = 'any';
        document.getElementById('request-security').value = 'public';
        document.getElementById('request-compliance').value = '';
        
        document.getElementById('search-results-card').style.display = 'none';
    }

    getCurrentRequestId() {
        // This would be set when searching for a specific request
        return this.currentRequestId || 'current-request-id';
    }

    // Additional methods for rule management
    async testRule(ruleId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/rules/${ruleId}/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            this.showSuccess(`Правило протестировано: ${result.message}`);
        } catch (error) {
            console.error('Error testing rule:', error);
            this.showError('Ошибка при тестировании правила: ' + error.message);
        }
    }

    async editRule(ruleId) {
        // Find the rule in the rules array
        const rule = this.rules.find(r => r.id === ruleId);
        if (!rule) {
            this.showError('Правило не найдено');
            return;
        }
        
        // Populate the form with rule data
        document.getElementById('rule-name').value = rule.name;
        document.getElementById('rule-description').value = rule.description;
        document.getElementById('rule-priority').value = rule.priority;
        
        // Clear existing conditions
        const conditionsContainer = document.getElementById('rule-conditions');
        conditionsContainer.innerHTML = '';
        
        // Add conditions from the rule
        rule.conditions.forEach(condition => {
            addCondition();
            const lastCondition = conditionsContainer.lastElementChild;
            lastCondition.querySelector('.field-select').value = condition.field;
            lastCondition.querySelector('.operator-select').value = condition.operator;
            lastCondition.querySelector('.value-input').value = condition.value;
        });
        
        this.updateRulePreview();
        this.showSuccess('Правило загружено для редактирования');
    }

    async deleteRule(ruleId) {
        if (!confirm('Вы уверены, что хотите удалить это правило?')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/rules/${ruleId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.showSuccess('Правило успешно удалено');
            this.loadRules();
        } catch (error) {
            console.error('Error deleting rule:', error);
            this.showError('Ошибка при удалении правила: ' + error.message);
        }
    }

    showExecutorDetails(executorId) {
        const executor = this.executors.find(e => e.id === executorId);
        if (!executor) {
            this.showError('Исполнитель не найден');
            return;
        }
        
        // Create a modal or show details
        const details = `
            <div class="card">
                <div class="card-header">
                    <h5>Детали исполнителя: ${executor.name}</h5>
                </div>
                <div class="card-body">
                    <p><strong>Email:</strong> ${executor.email}</p>
                    <p><strong>Роль:</strong> ${this.getRoleDisplayName(executor.role)}</p>
                    <p><strong>Вес:</strong> ${executor.weight}</p>
                    <p><strong>Статус:</strong> ${this.getStatusDisplayName(executor.status)}</p>
                    <p><strong>Опыт работы:</strong> ${executor.experience_years} лет</p>
                    <p><strong>Специализация:</strong> ${executor.specialization}</p>
                    <p><strong>Языковые навыки:</strong> ${executor.language_skills}</p>
                    <p><strong>Часовой пояс:</strong> ${executor.timezone}</p>
                    <p><strong>Дневной лимит:</strong> ${executor.daily_limit}</p>
                    <p><strong>Активных заявок:</strong> ${executor.active_requests_count}</p>
                    <p><strong>Процент успешности:</strong> ${(executor.success_rate * 100).toFixed(1)}%</p>
                </div>
            </div>
        `;
        
        // Show in a modal or alert
        alert(details);
    }

    searchExecutorsForRequest(requestId) {
        const request = this.requests.find(r => r.id === requestId);
        if (!request) {
            this.showError('Заявка не найдена');
            return;
        }
        
        // Populate search form with request data
        document.getElementById('request-title').value = request.title;
        document.getElementById('request-priority').value = request.priority;
        document.getElementById('request-weight').value = request.weight;
        document.getElementById('request-category').value = request.category;
        document.getElementById('request-complexity').value = request.complexity;
        document.getElementById('request-estimated-hours').value = request.estimated_hours;
        document.getElementById('request-skills').value = request.required_skills.join(', ');
        document.getElementById('request-language').value = request.language_requirement;
        document.getElementById('request-client-type').value = request.client_type;
        document.getElementById('request-urgency').value = request.urgency;
        document.getElementById('request-budget').value = request.budget || '';
        document.getElementById('request-tech-stack').value = request.technology_stack.join(', ');
        document.getElementById('request-timezone').value = request.timezone_requirement;
        document.getElementById('request-security').value = request.security_clearance;
        document.getElementById('request-compliance').value = request.compliance_requirements.join(', ');
        
        // Switch to search tab
        const searchTab = document.getElementById('search-tab');
        searchTab.click();
        
        // Store current request ID for assignment
        this.currentRequestId = requestId;
        
        this.showSuccess('Параметры заявки загружены для поиска исполнителей');
    }
}

// Global functions for HTML onclick handlers
function addCondition() {
    const container = document.getElementById('rule-conditions');
    const newCondition = document.createElement('div');
    newCondition.className = 'rule-condition';
    newCondition.innerHTML = `
        <div class="row">
            <div class="col-md-4">
                <label class="form-label">Поле</label>
                <select class="form-select field-select" onchange="updateOperators(this)">
                    <option value="">Выберите поле</option>
                    <optgroup label="Исполнитель">
                        <option value="role">Роль</option>
                        <option value="weight">Вес</option>
                        <option value="status">Статус</option>
                        <option value="active_requests_count">Количество активных заявок</option>
                        <option value="success_rate">Процент успешности</option>
                        <option value="daily_limit">Дневной лимит</option>
                        <option value="experience_years">Опыт работы (лет)</option>
                        <option value="specialization">Специализация</option>
                        <option value="language_skills">Языковые навыки</option>
                        <option value="timezone">Часовой пояс</option>
                        <option value="availability_hours">Часы доступности</option>
                        <option value="max_concurrent_tasks">Максимум одновременных задач</option>
                        <option value="response_time_minutes">Время ответа (мин)</option>
                        <option value="quality_rating">Рейтинг качества</option>
                        <option value="certification_level">Уровень сертификации</option>
                        <option value="department">Отдел</option>
                        <option value="manager_id">ID менеджера</option>
                        <option value="cost_per_hour">Стоимость за час</option>
                        <option value="location">Местоположение</option>
                        <option value="remote_work">Удаленная работа</option>
                        <option value="equipment_required">Требуемое оборудование</option>
                    </optgroup>
                    <optgroup label="Заявка">
                        <option value="priority">Приоритет</option>
                        <option value="request_weight">Вес заявки</option>
                        <option value="request_status">Статус заявки</option>
                        <option value="deadline">Дедлайн</option>
                        <option value="category">Категория</option>
                        <option value="complexity">Сложность</option>
                        <option value="estimated_hours">Оценочные часы</option>
                        <option value="client_type">Тип клиента</option>
                        <option value="urgency">Срочность</option>
                        <option value="budget">Бюджет</option>
                        <option value="technology_stack">Технологический стек</option>
                        <option value="required_skills">Требуемые навыки</option>
                        <option value="language_requirement">Требования к языку</option>
                        <option value="timezone_requirement">Требования к часовому поясу</option>
                        <option value="security_clearance">Уровень безопасности</option>
                        <option value="compliance_requirements">Требования соответствия</option>
                    </optgroup>
                </select>
            </div>
            <div class="col-md-3">
                <label class="form-label">Оператор</label>
                <select class="form-select operator-select">
                    <option value="equals">Равно</option>
                    <option value="not_equals">Не равно</option>
                    <option value="greater_than">Больше</option>
                    <option value="less_than">Меньше</option>
                    <option value="greater_than_or_equal">Больше или равно</option>
                    <option value="less_than_or_equal">Меньше или равно</option>
                    <option value="contains">Содержит</option>
                    <option value="in">В списке</option>
                    <option value="not_in">Не в списке</option>
                </select>
            </div>
            <div class="col-md-4">
                <label class="form-label">Значение</label>
                <input type="text" class="form-control value-input" placeholder="Введите значение">
            </div>
            <div class="col-md-1">
                <label class="form-label">&nbsp;</label>
                <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeCondition(this)">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
    container.appendChild(newCondition);
    app.updateRulePreview();
}

function removeCondition(button) {
    button.closest('.rule-condition').remove();
    app.updateRulePreview();
}

function updateOperators(select) {
    // This function can be used to update available operators based on field type
    // For now, we'll keep all operators available
}

function saveRule() {
    app.saveRule();
}

function testRule() {
    app.updateRulePreview();
}

// Additional methods for rule management
async function testRuleById(ruleId) {
    try {
        const response = await fetch(`${app.apiBaseUrl}/rules/${ruleId}/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        app.showSuccess(`Правило протестировано: ${result.message}`);
    } catch (error) {
        console.error('Error testing rule:', error);
        app.showError('Ошибка при тестировании правила: ' + error.message);
    }
}

async function editRule(ruleId) {
    // Find the rule in the rules array
    const rule = app.rules.find(r => r.id === ruleId);
    if (!rule) {
        app.showError('Правило не найдено');
        return;
    }
    
    // Populate the form with rule data
    document.getElementById('rule-name').value = rule.name;
    document.getElementById('rule-description').value = rule.description;
    document.getElementById('rule-priority').value = rule.priority;
    
    // Clear existing conditions
    const conditionsContainer = document.getElementById('rule-conditions');
    conditionsContainer.innerHTML = '';
    
    // Add conditions from the rule
    rule.conditions.forEach(condition => {
        addCondition();
        const lastCondition = conditionsContainer.lastElementChild;
        lastCondition.querySelector('.field-select').value = condition.field;
        lastCondition.querySelector('.operator-select').value = condition.operator;
        lastCondition.querySelector('.value-input').value = condition.value;
    });
    
    app.updateRulePreview();
    app.showSuccess('Правило загружено для редактирования');
}

async function deleteRule(ruleId) {
    if (!confirm('Вы уверены, что хотите удалить это правило?')) {
        return;
    }
    
    try {
        const response = await fetch(`${app.apiBaseUrl}/rules/${ruleId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        app.showSuccess('Правило успешно удалено');
        app.loadRules();
    } catch (error) {
        console.error('Error deleting rule:', error);
        app.showError('Ошибка при удалении правила: ' + error.message);
    }
}

function showExecutorDetails(executorId) {
    const executor = app.executors.find(e => e.id === executorId);
    if (!executor) {
        app.showError('Исполнитель не найден');
        return;
    }
    
    // Create a modal or show details
    const details = `
        <div class="card">
            <div class="card-header">
                <h5>Детали исполнителя: ${executor.name}</h5>
            </div>
            <div class="card-body">
                <p><strong>Email:</strong> ${executor.email}</p>
                <p><strong>Роль:</strong> ${app.getRoleDisplayName(executor.role)}</p>
                <p><strong>Вес:</strong> ${executor.weight}</p>
                <p><strong>Статус:</strong> ${app.getStatusDisplayName(executor.status)}</p>
                <p><strong>Опыт работы:</strong> ${executor.experience_years} лет</p>
                <p><strong>Специализация:</strong> ${executor.specialization}</p>
                <p><strong>Языковые навыки:</strong> ${executor.language_skills}</p>
                <p><strong>Часовой пояс:</strong> ${executor.timezone}</p>
                <p><strong>Дневной лимит:</strong> ${executor.daily_limit}</p>
                <p><strong>Активных заявок:</strong> ${executor.active_requests_count}</p>
                <p><strong>Процент успешности:</strong> ${(executor.success_rate * 100).toFixed(1)}%</p>
            </div>
        </div>
    `;
    
    // Show in a modal or alert
    alert(details);
}

function searchExecutorsForRequest(requestId) {
    const request = app.requests.find(r => r.id === requestId);
    if (!request) {
        app.showError('Заявка не найдена');
        return;
    }
    
    // Populate search form with request data
    document.getElementById('request-title').value = request.title;
    document.getElementById('request-priority').value = request.priority;
    document.getElementById('request-weight').value = request.weight;
    document.getElementById('request-category').value = request.category;
    document.getElementById('request-complexity').value = request.complexity;
    document.getElementById('request-estimated-hours').value = request.estimated_hours;
    document.getElementById('request-skills').value = request.required_skills.join(', ');
    document.getElementById('request-language').value = request.language_requirement;
    document.getElementById('request-client-type').value = request.client_type;
    document.getElementById('request-urgency').value = request.urgency;
    document.getElementById('request-budget').value = request.budget || '';
    document.getElementById('request-tech-stack').value = request.technology_stack.join(', ');
    document.getElementById('request-timezone').value = request.timezone_requirement;
    document.getElementById('request-security').value = request.security_clearance;
    document.getElementById('request-compliance').value = request.compliance_requirements.join(', ');
    
    // Switch to search tab
    const searchTab = document.getElementById('search-tab');
    searchTab.click();
    
    // Store current request ID for assignment
    app.currentRequestId = requestId;
    
    app.showSuccess('Параметры заявки загружены для поиска исполнителей');
}

function searchExecutors() {
    app.searchExecutors();
}

function clearSearch() {
    app.clearSearch();
}

function showAddExecutorModal() {
    new bootstrap.Modal(document.getElementById('addExecutorModal')).show();
}

function showAddRequestModal() {
    new bootstrap.Modal(document.getElementById('addRequestModal')).show();
}

function addExecutor() {
    const form = document.getElementById('add-executor-form');
    const formData = new FormData(form);
    const executorData = Object.fromEntries(formData.entries());
    
    // Convert string values to appropriate types
    executorData.weight = parseFloat(executorData.weight);
    executorData.experience_years = parseInt(executorData.experience_years);
    executorData.daily_limit = parseInt(executorData.daily_limit);
    
    // Set default values for missing fields
    executorData.active_requests_count = 0;
    executorData.success_rate = 0.0;
    executorData.parameters = {};
    
    console.log('Sending executor data:', executorData);
    
    fetch(`${app.apiBaseUrl}/executors`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(executorData)
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                throw new Error(`HTTP error! status: ${response.status}, body: ${text}`);
            });
        }
        return response.json();
    })
    .then(data => {
        app.showSuccess('Исполнитель успешно добавлен');
        bootstrap.Modal.getInstance(document.getElementById('addExecutorModal')).hide();
        app.loadExecutors();
        app.loadDashboardData();
    })
    .catch(error => {
        console.error('Error adding executor:', error);
        app.showError('Ошибка при добавлении исполнителя: ' + error.message);
    });
}

function addRequest() {
    const form = document.getElementById('add-request-form');
    const formData = new FormData(form);
    const requestData = Object.fromEntries(formData.entries());
    
    // Convert string values to appropriate types
    requestData.weight = parseFloat(requestData.weight);
    requestData.estimated_hours = parseInt(requestData.estimated_hours);
    
    // Convert comma-separated strings to arrays
    if (requestData.required_skills && requestData.required_skills.trim()) {
        requestData.required_skills = requestData.required_skills.split(',').map(s => s.trim()).filter(s => s);
    } else {
        requestData.required_skills = [];
    }
    
    if (requestData.technology_stack && requestData.technology_stack.trim()) {
        requestData.technology_stack = requestData.technology_stack.split(',').map(s => s.trim()).filter(s => s);
    } else {
        requestData.technology_stack = [];
    }
    
    if (requestData.compliance_requirements && requestData.compliance_requirements.trim()) {
        requestData.compliance_requirements = requestData.compliance_requirements.split(',').map(s => s.trim()).filter(s => s);
    } else {
        requestData.compliance_requirements = [];
    }
    
    // Convert budget to integer if provided
    if (requestData.budget) {
        requestData.budget = parseInt(requestData.budget);
    } else {
        requestData.budget = null;
    }
    
    console.log('Sending request data:', requestData);
    
    fetch(`${app.apiBaseUrl}/requests`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                throw new Error(`HTTP error! status: ${response.status}, body: ${text}`);
            });
        }
        return response.json();
    })
    .then(data => {
        app.showSuccess('Заявка успешно создана');
        bootstrap.Modal.getInstance(document.getElementById('addRequestModal')).hide();
        app.loadRequests();
        app.loadDashboardData();
    })
    .catch(error => {
        console.error('Error adding request:', error);
        app.showError('Ошибка при создании заявки: ' + error.message);
    });
}

// Export functions
function exportDashboardExcel() {
    try {
        const link = document.createElement('a');
        link.href = '/metrics/export/excel';
        link.download = `dashboard_metrics_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        app.showSuccess('Экспорт дашборда в Excel запущен');
    } catch (error) {
        console.error('Error exporting dashboard:', error);
        app.showError('Ошибка экспорта дашборда: ' + error.message);
    }
}

function exportExecutorsExcel() {
    try {
        const link = document.createElement('a');
        link.href = '/metrics/export/executors/excel';
        link.download = `executors_performance_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        app.showSuccess('Экспорт исполнителей в Excel запущен');
    } catch (error) {
        console.error('Error exporting executors:', error);
        app.showError('Ошибка экспорта исполнителей: ' + error.message);
    }
}

function openGrafana() {
    try {
        window.open('http://localhost:3000', '_blank');
        app.showSuccess('Открыт Grafana Dashboard');
    } catch (error) {
        console.error('Error opening Grafana:', error);
        app.showError('Ошибка открытия Grafana: ' + error.message);
    }
}

// Initialize the application
let app;
document.addEventListener('DOMContentLoaded', function() {
    app = new ExecutorBalancerApp();
    
    // Add event listeners for rule preview updates
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('field-select') || 
            e.target.classList.contains('operator-select') || 
            e.target.classList.contains('value-input')) {
            app.updateRulePreview();
        }
    });
    
    // Auto-refresh dashboard every 30 seconds for real-time updates
    setInterval(() => {
        app.loadDashboardData();
    }, 30000);
});
