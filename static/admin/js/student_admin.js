
(function($) {
    $(document).ready(function() {
        // Function to toggle visibility of diocese and congregation fields
        function toggleAffiliationFields() {
            var studentType = $('#id_student_type').val();
            var dioceseField = $('.field-diocese');
            var congregationField = $('.field-congregation');

            if (studentType === 'diocesan') {
                dioceseField.show();
                congregationField.hide();
            } else if (studentType === 'congregation') {
                dioceseField.hide();
                congregationField.show();
            } else {
                dioceseField.show();
                congregationField.show();
            }
        }

        // Initial toggle on page load
        toggleAffiliationFields();

        // Toggle when student_type changes
        $('#id_student_type').change(function() {
            toggleAffiliationFields();
        });
    });
})(django.jQuery);
