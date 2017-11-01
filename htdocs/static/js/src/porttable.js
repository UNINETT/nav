define(function(require) {

    var DataTables = require('libs/datatables.min');
    var moduleSort = require('dt_plugins/modulesort');
    var URI = require('libs/urijs/URI');
    var Moment = require('moment');


    /*
     * dtColumns defines the data we want to use from the result set from the
     * api. They are in order of appearance in the table - changes here may need
     * changes in the template aswell.

     * _data_ defines what key to look up for the value in the column
     *
     * _type_ defines a type needed for using the correct sorting function
     *        (added by adding functions to $.fn.dataTable.ext.type.order)
     **
     * _render_ completely overrides the default rendering of the value
     */
    var dtColumns = [
        {
            render: function(data, type, row, meta) {
                return '<a href="' + NAV.urls.portadmin_index + row.id + '" title="Configure port in Portadmin"><img src="/static/images/toolbox/portadmin.svg" style="height: 1em; width: 1em" /></a>';
            },
            orderable: false
        },

        {
            data: "ifname",
            type: "module",
            render: function(data, type, row, meta) {
                return '<a href="' + row.object_url + '">' + data + '</a>';
            }
        },

        {
            data: "ifalias",
            render: function(data, type, row, meta) {
                return '<a href="' + row.object_url + '">' + data + '</a>';
            }
        },

        {
            data: 'module',
            render: function(data, type, row, meta) {
                return data
                    ? '<a href="' + data.object_url + '">' + data.name + '</a>'
                    : '';
            }
        },

        {
            data: "ifadminstatus",
            type: "statuslight",
            render: renderStatus
        },

        {
            data: "ifoperstatus",
            type: "statuslight",
            render: renderStatus
        },

        {
            data: "vlan",
            render: function(data, type, row, meta) {
                if (row['trunk']) {
                    return "<span title='Trunk' style='border: 3px double black; padding: 0 5px'>" + data + "</span>"
                }
                return data;
            }
        },

        {
            data: "speed",
            render: function(data, type, row, meta) {
                if (row.duplex === 'h') {
                    return data + '<span class="label warning" title="Half duplex" style="margin-left: .3rem">HD</span>';
                }
                return row.speed ? data : "";
            }
        },

        // Last used
        {
            render: function(data, type, row, meta) {
                if (row.last_used) {
                    var date = new Date(row.last_used.end_time);
                    return date.getYear() > 5000 ? "Now" : Moment(row.last_used.end_time).format('YYYY-MM-DD HH:mm:ss');
                } else {
                    if (row.last_used === undefined) {
                        // Display this when no data loaded
                        return ''
                    }
                    if (row.last_used === null) {
                        // Display this for no last used in dataset
                        return '<span class="dim">Never</span>';
                    }
                    return '';
                }
            },
            visible: false
        },

        {
            data: 'to_netbox',
            render: function(data, type, row, meta) {
                return data
                    ? '<a href="' + data.object_url + '">' + data.sysname + '</a>'
                    : '';
            }
        },

        {
            data: 'to_interface',
            render: function(data, type, row, meta) {
                return data
                    ? '<a href="' + data.object_url + '">' + data.ifname + '</a>'
                    : '';
            }
        },

    ];


    /** Renders a light indicating status (red or green) */
    function renderStatus(data, type, row, meta) {
        var color = data === 2 ? 'red' : 'green';
        return '<img src="/static/images/lys/' + color + '.png">';
    }


    /**
     * Creates the checkboxes for filtering on ifclasses (swport, gwport, physicalport)
     */
    function createFilters(selector) {
        var $form = $("<form id='portlistform'>").appendTo(selector);
        var fs1 = $('<fieldset>').appendTo($form);
        var fs2 = $('<fieldset>').appendTo($form);
        fs1.append('<legend>Port filters</legend>')
        fs1.append('<label><input type="radio" name="portgroup" value="all" checked>All ports</label>');
        fs1.append('<label><input type="radio" name="portgroup" value="swport">Switch ports</label>');
        fs1.append('<label><input type="radio" name="portgroup" value="gwport">Router ports</label>');
        fs1.append('<label><input type="radio" name="portgroup" value="physicalport">Physical ports</label>');
        fs1.append('<label><input type="radio" name="portgroup" value="trunk">Trunks</label>');

        fs2.append('<legend>Optional</legend>')
        fs2.append('<label><input type="checkbox" name="last_used">Last used</label>');
        return $form;
    }


    /**
     * The searchdelay in DataTables starts whenever you start to write
     * (weird). Make it work so that the delay kicks in until you're actually
     * done typing.
     */
    function fixSearchDelay(dataTable) {
        $('div.dataTables_filter input').off('keyup.DT input.DT');

        var searchDelay = null,
            prevSearch = null;

        $('div.dataTables_filter input').on('keyup', function() {
            var search = $('div.dataTables_filter input').val();

            clearTimeout(searchDelay);

            if (search !== prevSearch) {
                searchDelay = setTimeout(function() {
                    prevSearch = search;
                    dataTable.search(search).draw();
                }, 400);
            }
        });
    }


    /**
     * Translate data keys from response to something datatables understand
     */
    function translateData(data) {
        var json = jQuery.parseJSON( data );
        json.recordsTotal = json.count;
        json.data = json.results;
        return JSON.stringify( json );
    }


    /** Custom ordering for statuslight as it cant sort on html elements */
    function addCustomOrdering() {
        $.fn.dataTable.ext.type.order['statuslight-pre'] = function ( data ) {
            return data;
        };
    }

    /**
     * The table to be instantiated
     * @param {string} selector - the jQuery selector for the table
     * @param {int} netboxid - the netboxid of the device to list ports for
     */
    function PortTable(selector, netboxid) {
        this.lastUsedCol = 8;

        this.netboxid = netboxid;
        this.selector = selector;
        this.formContainerSelector = '#ifclasses';
        this.dataTable = this.createDataTable();
        this.addFormListener(createFilters(this.formContainerSelector));
        $(this.selector).on('processing.dt', function(event, settings, processing) {
            if (processing) {
                $(this).css('opacity', .5);
            } else {
                $(this).css('opacity', 1);
            }
        })

        addCustomOrdering();
        fixSearchDelay(this.dataTable);
    }

    PortTable.prototype = {
        createDataTable: function() {
            // https://datatables.net/reference/option/
            return $(this.selector).DataTable({
                autoWidth: false,
                paging: false,
                processing: true,
                orderClasses: false,
                ajax: {
                    url: this.getUrl().toString(),
                    dataFilter: translateData
                },
                columns: dtColumns,
                order: [[1, 'asc']],
                dom: "f<'#ifclasses'><'#infoprocessing'ir>t",
                language: {
                    info: "_TOTAL_ entries",
                    processing: "Loading...",
                }
            });
        },

        /**
         * Load data using custom request because of chunked loading
         * I'm leaving this here as an example although it's not in use
         * Remember to adjust page_size
         */
        loadData: function() {
            var self = this;

            function loadMoreData(data) {
                self.dataTable.rows.add(data.results).draw();
                if (data.next) {
                    $.get(data.next, loadMoreData);
                } else {
                    $('#portlist_processing').hide();
                }
            }

            $('#portlist_processing').show();
            $.get(this.getUrl(), loadMoreData)
        },

        /** Listen to changes in form */
        addFormListener: function($form) {
            var self = this;
            var column = self.dataTable.column(this.lastUsedCol);
            $form.on('change', function() {
                var newUrl = self
                    .getUrl()
                    .setSearch('ifclass[]', $form.find('[name=portgroup]:checked').val())
                if ($form.get(0).elements.last_used.checked) {
                    newUrl.setSearch('last_used', 1);
                    column.visible(true);
                } else {
                    column.visible(false);
                }
                console.log(newUrl.toString());
                self.dataTable.ajax.url(newUrl.toString()).load();
            });
        },

        getUrl: function() {
            return URI("/api/1/interface/")
                .addSearch('page_size', 10000)
                .addSearch('netbox', this.netboxid);
        }

    }


    return PortTable;

});