(function($) {
    $(document).ready(function() {
        function toggleCustomField(selectId, fieldClass) {
            var $select = $(selectId);
            var $field = $(fieldClass).closest('.form-row');
            if (!$select.length || !$field.length) return;

            function update() {
                if ($select.val() === '__custom__') {
                    $field.slideDown(200);
                } else {
                    $field.slideUp(200);
                    $field.find('input').val('');
                }
            }
            $select.on('change', update);
            update();
        }

        toggleCustomField('#id_chapter', '.field-custom_chapter_name');
        toggleCustomField('#id_topic', '.field-custom_topic_name');
    });
})(django.jQuery);
